from __future__ import annotations

import json
import operator
from typing import Annotated, Any, Literal, Optional

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from src.llm_provider import get_llm
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


ROUTER_SYSTEM = """
You are a legislative AI router. Given a user query, extract:
1. task — one of: "single" | "compare" | "memo"
   - "single"  → analyze one bill for impact
   - "compare" → compare two or more bills
   - "memo"    → draft a policy memo from one or more bills
2. bill_ids — list of bill numbers (integers as strings) mentioned. 
   If none explicitly mentioned, return [].

Respond ONLY with a JSON object — no markdown, no preamble:
{"task": "...", "bill_ids": ["...", ...]}
"""


def router_node(state: AgentState, config: RunnableConfig) -> dict:
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

    return {
        "task": task,
        "bill_ids": bill_ids,
        "messages": [response],
    }


def research_node(state: AgentState, config: RunnableConfig) -> dict:
    """Runs ChromaDB retrieval + web search in parallel (per bill)."""
    bill_ids = state["bill_ids"]
    retrieved: dict[str, list[str]] = {}
    web: dict[str, list[str]] = {}

    for bid in bill_ids:
        chunks = retrieve_bill_chunks(bid, k=6)
        retrieved[bid] = chunks

        snippets = web_search_bill(bid)
        web[bid] = snippets

    return {
        "retrieved_chunks": retrieved,
        "web_snippets": web,
        "messages": [HumanMessage(content=f"Research complete for bills: {bill_ids}")],
    }


ANALYST_SYSTEM = """
You are a senior legislative policy analyst. Given retrieved bill text and recent web context,
produce a structured analysis. Respond ONLY with valid JSON matching this exact schema:

{
  "risk_scores":      { "<bill_id>": { "<Sector>": <1-5>, ... } },
  "sectors":          { "<bill_id>": ["Sector", ...] },
  "impacted_states":  { "<bill_id>": ["ST", ...] },
  "comparison":       null   // OR an object if multiple bills
}

For comparison (multiple bills), add:
  "comparison": {
    "winner": "<bill_id>",
    "rationale": "...",
    "head_to_head": { "<Sector>": { "<bill_id>": <score>, ... } }
  }

No markdown. No preamble.
"""


def analysis_node(state: AgentState, config: RunnableConfig) -> dict:
    llm = get_llm(config)

    context_blocks = []
    for bid in state["bill_ids"]:
        chunks = state["retrieved_chunks"].get(bid, [])
        snippets = state["web_snippets"].get(bid, [])
        context_blocks.append(
            f"=== BILL {bid} ===\n"
            f"[Vector Store]\n" + "\n".join(chunks[:4]) + "\n"
            f"[Web Context]\n" + "\n".join(snippets[:3])
        )

    context = "\n\n".join(context_blocks)
    messages = [
        SystemMessage(content=ANALYST_SYSTEM),
        HumanMessage(content=f"Analyze the following bill(s):\n\n{context}"),
    ]
    response = llm.invoke(messages)

    try:
        raw = response.content.strip().strip("```json").strip("```").strip()
        data = json.loads(raw)
    except Exception:
        data = {
            "risk_scores": {},
            "sectors": {},
            "impacted_states": {},
            "comparison": None,
        }

    return {
        "risk_scores": data.get("risk_scores", {}),
        "sectors": data.get("sectors", {}),
        "impacted_states": data.get("impacted_states", {}),
        "comparison": data.get("comparison"),
        "messages": [response],
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

    return {
        "summary": text if task != "memo" else text[:500] + "...",
        "memo": text if task == "memo" else None,
        "messages": [response],
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
