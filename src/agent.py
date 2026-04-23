from __future__ import annotations

import json
import operator
import time
from typing import Annotated, Any, Literal, Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from src.llm_provider import get_llm
from src.metrics import (
    record_analysis_parse,
    record_latency,
    record_query_start,
    record_retrieval,
    record_web_search,
)
from src.tools import (
    compare_bills_tool,
    retrieve_bill_chunks,
    web_search_bill,
)


class AgentState(TypedDict):
    query: str

    task: Literal["single", "compare", "memo"]

    bill_ids: list[str]

    retrieved_chunks: dict[str, list[str]]
    web_snippets: dict[str, list[str]]

    risk_scores: dict[str, Any]
    sectors: dict[str, list[str]]
    impacted_states: dict[str, list[str]]
    comparison: Optional[dict[str, Any]]

    summary: str
    memo: Optional[str]

    messages: Annotated[list[BaseMessage], add_messages]

    model_tag: str

    t_router_ms: int
    t_research_ms: int
    t_analysis_ms: int
    t_writer_ms: int


ROUTER_SYSTEM = """
You are a legislative AI router. Given a user query, extract:
1. task — one of: "single" | "compare" | "memo"
2. bill_ids — list of bill numbers explicitly mentioned in a legislative context.
 
STRICT RULES:
- Only extract bill numbers when the query clearly refers to legislation.
  Valid: "analyze bill 42", "compare bills 4 and 108", "H.R. 77", "S. 12"
  Invalid: random strings, gibberish, numbers with no legislative context
- If the query is gibberish, nonsensical, or contains no clear legislative intent,
  return bill_ids as an empty list [].
- Never extract numbers that appear incidentally (e.g. "top 5 tips", "room 6").
 
Respond ONLY with a JSON object — no markdown, no preamble:
{"task": "...", "bill_ids": ["...", ...]}
"""


def router_node(state: AgentState, config: RunnableConfig) -> dict:
    t0 = time.time()
    llm = get_llm(config)
    messages = [
        SystemMessage(content=ROUTER_SYSTEM),
        HumanMessage(content=state["query"]),
    ]
    response = llm.invoke(messages)
    try:
        parsed = json.loads(
            response.content.strip().strip("```json").strip("```"))
        task = parsed.get("task", "single")
        bill_ids = [str(b) for b in parsed.get("bill_ids", [])]
    except Exception:
        task = "single"
        bill_ids = []

    elapsed_ms = int((time.time() - t0) * 1000)
    record_query_start(task, bill_ids)

    return {
        "task": task,
        "bill_ids": bill_ids,
        "messages": [response],
        "t_router_ms": elapsed_ms,
        "t_research_ms": 0,
        "t_analysis_ms": 0,
        "t_writer_ms": 0,
    }


def research_node(state: AgentState, config: RunnableConfig) -> dict:
    """Runs ChromaDB retrieval + web search in parallel (per bill)."""
    t0 = time.time()
    bill_ids = state["bill_ids"]
    retrieved: dict[str, list[str]] = {}
    web: dict[str, list[str]] = {}

    for bid in bill_ids:
        chunks = retrieve_bill_chunks(bid, k=6)
        used_fallback = len(chunks) > 0 and not any(
            bid in c for c in chunks[:2])
        record_retrieval(bid, len(chunks), used_fallback=used_fallback)
        retrieved[bid] = chunks

        snippets = web_search_bill(bid)
        success = len(snippets) > 0 and not snippets[0].startswith(
            "[Web search")
        record_web_search(len(snippets), success=success)
        web[bid] = snippets

    elapsed_ms = int((time.time() - t0) * 1000)

    return {
        "retrieved_chunks": retrieved,
        "web_snippets": web,
        "messages": [HumanMessage(content=f"Research complete for bills: {bill_ids}")],
        "t_research_ms": elapsed_ms,
    }


ANALYST_SYSTEM = """
You are a senior legislative policy analyst. Given retrieved bill text and recent web context,
produce a structured analysis. Respond ONLY with valid JSON matching this exact schema:

{
  "risk_scores":      { "<bill_number>": { "<Sector>": <1-5>, ... } },
  "sectors":          { "<bill_number>": ["Sector", ...] },
  "impacted_states":  { "<bill_number>": ["ST", ...] },
  "comparison":       null
}

CRITICAL: Use ONLY the bare bill number as keys (e.g. "4", "108") — never "BILL 4" or "bill 4".

For comparison (multiple bills), set comparison to:
  {
    "winner": "<bill_number>",
    "rationale": "...",
    "head_to_head": { "<Sector>": { "<bill_number>": <score>, ... } }
  }

No markdown. No preamble. No extra keys.
"""


def analysis_node(state: AgentState, config: RunnableConfig) -> dict:
    t0 = time.time()
    llm = get_llm(config)

    # Build context block per bill
    context_blocks = []
    for bid in state["bill_ids"]:
        chunks = state["retrieved_chunks"].get(bid, [])
        snippets = state["web_snippets"].get(bid, [])
        # Trim aggressively — 600 chars per chunk, 2 chunks, 1 snippet
        # keeps the prompt under ~1 000 tokens so Analysis node stays fast
        trimmed_chunks = [c[:600] for c in chunks[:2]]
        trimmed_snippets = [s[:300] for s in snippets[:1]]
        context_blocks.append(
            f"=== BILL {bid} ===\n"
            f"[Vector Store]\n" + "\n".join(trimmed_chunks) + "\n"
            f"[Web Context]\n" + "\n".join(trimmed_snippets)
        )

    context = "\n\n".join(context_blocks)
    messages = [
        SystemMessage(content=ANALYST_SYSTEM),
        HumanMessage(content=f"Analyze the following bill(s):\n\n{context}"),
    ]
    response = llm.invoke(messages)

    parse_success = True
    try:
        raw = response.content.strip().strip("```json").strip("```").strip()
        data = json.loads(raw)
    except Exception:
        parse_success = False
        data = {
            "risk_scores": {},
            "sectors": {},
            "impacted_states": {},
            "comparison": None,
        }

    record_analysis_parse(parse_success)
    elapsed_ms = int((time.time() - t0) * 1000)

    return {
        "risk_scores": data.get("risk_scores", {}),
        "sectors": data.get("sectors", {}),
        "impacted_states": data.get("impacted_states", {}),
        "comparison": data.get("comparison"),
        "messages": [response],
        "t_analysis_ms": elapsed_ms,
    }


WRITER_SYSTEM_SUMMARY = """
You are a concise policy communications expert. Write a 3–4 sentence executive summary
of the bill analysis. Be direct. No bullet points. Reference specific sectors and states.
"""

WRITER_SYSTEM_MEMO = """
You are a senior policy advisor drafting a formal policy memo.

Structure:
TO: Legislative Affairs Committee
FROM: LegislAI Intelligence Engine
RE: [Bill Title / Comparison]
DATE: [Today]

EXECUTIVE SUMMARY
BACKGROUND
KEY FINDINGS (sector impacts, state effects)
RISK ASSESSMENT
RECOMMENDATIONS

Tone: authoritative but accessible. 400–600 words.
"""


def writer_node(state: AgentState, config: RunnableConfig) -> dict:
    t0 = time.time()
    llm = get_llm(config)
    task = state["task"]

    context = json.dumps({
        "bill_ids": state["bill_ids"],
        "risk_scores": state["risk_scores"],
        "sectors": state["sectors"],
        "impacted_states": state["impacted_states"],
        "comparison": state["comparison"],
        "web_snippets": state["web_snippets"],
    }, indent=2)

    system = WRITER_SYSTEM_MEMO if task == "memo" else WRITER_SYSTEM_SUMMARY
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=f"Analysis data:\n{context}"),
    ]
    response = llm.invoke(messages)
    text = response.content.strip()

    elapsed_ms = int((time.time() - t0) * 1000)

    record_latency(
        router_ms=state.get("t_router_ms", 0),
        research_ms=state.get("t_research_ms", 0),
        analysis_ms=state.get("t_analysis_ms", 0),
        writer_ms=elapsed_ms,
    )

    return {
        "summary": text if task != "memo" else text[:500] + "...",
        "memo": text if task == "memo" else None,
        "messages": [response],
        "t_writer_ms": elapsed_ms,
    }


def needs_bill_ids(state: AgentState) -> Literal["research", "end"]:
    """If router couldn't extract any bill IDs, bail early."""
    return "research" if state["bill_ids"] else "end"


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("router",   router_node)
    graph.add_node("research", research_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("writer",   writer_node)

    graph.set_entry_point("router")

    graph.add_conditional_edges(
        "router",
        needs_bill_ids,
        {"research": "research", "end": END},
    )
    graph.add_edge("research", "analysis")
    graph.add_edge("analysis", "writer")
    graph.add_edge("writer", END)

    return graph.compile()


legislai_graph = build_graph()
