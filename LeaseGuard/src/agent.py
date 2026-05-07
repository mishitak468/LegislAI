"""
LeaseGuard — Agentic RAG Pipeline (LangGraph)
==============================================
Graph: RouterNode → ResearchNode → AnalysisNode → WriterNode

Same architecture as LegislAI — swapped domain:
  - Corpus:  user-uploaded lease PDF + pre-ingested state tenant law docs
  - Router:  detects task (flag_risks | explain_clause | compare | rights)
  - Research: retrieves lease chunks + matching state law chunks
  - Analysis: scores clause risk 1-5 by category
  - Writer:  plain-English summary, negotiation tips, rights explanation
"""

from __future__ import annotations

import json
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
from src.tools import retrieve_lease_chunks, retrieve_law_chunks, web_search_tenant_law


# ─────────────────────────────────────────────
# SHARED STATE
# ─────────────────────────────────────────────

class AgentState(TypedDict):
    query: str
    state_code: str                          # e.g. "NY", "CA" — for law retrieval
    task: Literal["flag_risks", "explain_clause", "compare", "rights", "summary"]

    # Research artifacts
    lease_chunks: list[str]                  # from uploaded lease
    law_chunks: list[str]                    # from state tenant law corpus
    web_snippets: list[str]                  # live Tavily results

    # Analysis results
    risk_scores: dict[str, Any]              # { "Early Termination": 4, ... }
    flagged_clauses: list[dict[str, Any]]    # [{ clause, risk, reason, negotiate }]
    illegal_clauses: list[str]               # clauses that violate state law
    tenant_rights: list[str]                 # relevant rights from state law

    # Output
    summary: str
    negotiation_tips: list[str]
    disclaimer: str

    messages: Annotated[list[BaseMessage], add_messages]
    model_tag: str

    # Node timing
    t_router_ms: int
    t_research_ms: int
    t_analysis_ms: int
    t_writer_ms: int


# ─────────────────────────────────────────────
# NODE 1: ROUTER
# ─────────────────────────────────────────────

ROUTER_SYSTEM = """
You are a lease analysis router. Given a user query about a rental lease, extract:
1. task — one of:
   - "flag_risks"      → find and score all risky clauses
   - "explain_clause"  → explain what a specific clause means
   - "compare"         → compare this lease to a standard lease
   - "rights"          → what are my rights regarding X
   - "summary"         → give me a plain-English summary of the whole lease
2. state_code — the 2-letter US state code if mentioned (e.g. "NY", "CA").
   If not mentioned, return "".

STRICT RULES:
- Only respond to queries clearly about a lease, rental agreement, or tenant rights.
- If the query is gibberish or unrelated to leases/renting, return task="flag_risks"
  and state_code="" as safe defaults.

Respond ONLY with valid JSON — no markdown, no preamble:
{"task": "...", "state_code": "..."}
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
        parsed = json.loads(response.content.strip().strip("```json").strip("```"))
        task       = parsed.get("task", "flag_risks")
        state_code = parsed.get("state_code", "").upper().strip()
    except Exception:
        task, state_code = "flag_risks", ""

    elapsed_ms = int((time.time() - t0) * 1000)
    record_query_start(task, [state_code] if state_code else [])

    return {
        "task": task,
        "state_code": state_code,
        "messages": [response],
        "t_router_ms": elapsed_ms,
        "t_research_ms": 0,
        "t_analysis_ms": 0,
        "t_writer_ms": 0,
    }


# ─────────────────────────────────────────────
# NODE 2: RESEARCH
# ─────────────────────────────────────────────

def research_node(state: AgentState, config: RunnableConfig) -> dict:
    t0 = time.time()

    # Retrieve from uploaded lease vector store
    lease_chunks = retrieve_lease_chunks(state["query"], k=6)
    record_retrieval("lease", len(lease_chunks), used_fallback=len(lease_chunks) == 0)

    # Retrieve matching state tenant law chunks
    law_chunks = retrieve_law_chunks(state["query"], state["state_code"], k=4)
    record_retrieval("law", len(law_chunks), used_fallback=len(law_chunks) == 0)

    # Live web search for state-specific tenant rights
    search_query = f"tenant rights {state['state_code']} lease {state['query'][:60]}"
    snippets = web_search_tenant_law(search_query)
    success = len(snippets) > 0 and not snippets[0].startswith("[Web search")
    record_web_search(len(snippets), success)

    elapsed_ms = int((time.time() - t0) * 1000)

    return {
        "lease_chunks": lease_chunks,
        "law_chunks": law_chunks,
        "web_snippets": snippets,
        "messages": [HumanMessage(content=f"Research complete: {len(lease_chunks)} lease chunks, {len(law_chunks)} law chunks")],
        "t_research_ms": elapsed_ms,
    }


# ─────────────────────────────────────────────
# NODE 3: ANALYSIS
# ─────────────────────────────────────────────

ANALYST_SYSTEM = """
You are a tenant rights legal analyst. Given lease text and relevant state tenant law,
produce a structured risk analysis.

Respond ONLY with valid JSON matching this exact schema — no markdown, no preamble:

{
  "risk_scores": {
    "Early Termination": <1-5>,
    "Rent Increases": <1-5>,
    "Security Deposit": <1-5>,
    "Subletting": <1-5>,
    "Repairs & Maintenance": <1-5>,
    "Landlord Entry & Privacy": <1-5>,
    "Renewal Terms": <1-5>,
    "Pet Policy": <1-5>
  },
  "flagged_clauses": [
    {
      "clause": "exact short quote from lease text",
      "risk": <1-5>,
      "reason": "why this is risky in plain English",
      "negotiate": "what to ask for instead"
    }
  ],
  "illegal_clauses": [
    "description of any clause that violates state law"
  ],
  "tenant_rights": [
    "relevant right the tenant has under state law"
  ]
}

Risk scale: 1=standard/fair, 2=slightly unfavorable, 3=watch this, 4=push back, 5=red flag.
Use ONLY scores 1-5 as integers. Use bare category names as keys, not quotes inside quotes.
If a category is not mentioned in the lease, score it 1.
Flag a maximum of 5 clauses — only the most important ones.
"""

def analysis_node(state: AgentState, config: RunnableConfig) -> dict:
    t0 = time.time()
    llm = get_llm(config)

    # Trim context to keep prompt fast
    lease_context  = "\n".join(c[:600] for c in state["lease_chunks"][:3])
    law_context    = "\n".join(c[:400] for c in state["law_chunks"][:2])
    web_context    = "\n".join(s[:300] for s in state["web_snippets"][:1])
    state_label    = f"State: {state['state_code']}" if state["state_code"] else "State: unknown"

    prompt = f"""
{state_label}
User question: {state['query']}

=== LEASE TEXT ===
{lease_context}

=== STATE TENANT LAW ===
{law_context}

=== WEB CONTEXT ===
{web_context}
"""
    messages = [
        SystemMessage(content=ANALYST_SYSTEM),
        HumanMessage(content=prompt),
    ]
    response = llm.invoke(messages)

    parse_success = True
    try:
        raw  = response.content.strip().strip("```json").strip("```").strip()
        data = json.loads(raw)
    except Exception:
        parse_success = False
        data = {
            "risk_scores": {},
            "flagged_clauses": [],
            "illegal_clauses": [],
            "tenant_rights": [],
        }

    record_analysis_parse(parse_success)
    elapsed_ms = int((time.time() - t0) * 1000)

    return {
        "risk_scores":     data.get("risk_scores", {}),
        "flagged_clauses": data.get("flagged_clauses", []),
        "illegal_clauses": data.get("illegal_clauses", []),
        "tenant_rights":   data.get("tenant_rights", []),
        "messages":        [response],
        "t_analysis_ms":   elapsed_ms,
    }


# ─────────────────────────────────────────────
# NODE 4: WRITER
# ─────────────────────────────────────────────

WRITER_SYSTEM = """
You are a tenant advocate writing plain-English lease summaries.
Your reader is a regular person who is not a lawyer.

Given the analysis data, write a clear, direct response that:
- Leads with the most important finding (highest risk or most urgent action)
- Uses simple language — no legal jargon without explanation
- Is specific — quote the actual clause when flagging something
- Gives concrete negotiation advice where relevant
- Is 150-250 words maximum

Do NOT say "based on the analysis" or "as an AI". Just write directly.
Do NOT provide legal advice — end with one sentence noting they should
consult a licensed attorney for their specific situation.
"""

def writer_node(state: AgentState, config: RunnableConfig) -> dict:
    t0 = time.time()
    llm = get_llm(config)

    context = json.dumps({
        "task":            state["task"],
        "state_code":      state["state_code"],
        "risk_scores":     state["risk_scores"],
        "flagged_clauses": state["flagged_clauses"],
        "illegal_clauses": state["illegal_clauses"],
        "tenant_rights":   state["tenant_rights"],
        "query":           state["query"],
    }, indent=2)

    messages = [
        SystemMessage(content=WRITER_SYSTEM),
        HumanMessage(content=context),
    ]
    response = llm.invoke(messages)
    text = response.content.strip()

    # Extract negotiation tips from flagged clauses
    tips = [
        f"**{fc['clause'][:60]}…** → {fc['negotiate']}"
        for fc in state.get("flagged_clauses", [])
        if fc.get("negotiate") and fc.get("risk", 0) >= 3
    ]

    elapsed_ms = int((time.time() - t0) * 1000)

    record_latency(
        router_ms=state.get("t_router_ms", 0),
        research_ms=state.get("t_research_ms", 0),
        analysis_ms=state.get("t_analysis_ms", 0),
        writer_ms=elapsed_ms,
    )

    return {
        "summary":           text,
        "negotiation_tips":  tips[:4],
        "disclaimer":        "⚠️ This is not legal advice. Consult a licensed attorney before making decisions about your lease.",
        "messages":          [response],
        "t_writer_ms":       elapsed_ms,
    }


# ─────────────────────────────────────────────
# GRAPH
# ─────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)
    graph.add_node("router",   router_node)
    graph.add_node("research", research_node)
    graph.add_node("analysis", analysis_node)
    graph.add_node("writer",   writer_node)
    graph.set_entry_point("router")
    graph.add_edge("router",   "research")
    graph.add_edge("research", "analysis")
    graph.add_edge("analysis", "writer")
    graph.add_edge("writer",   END)
    return graph.compile()


leaseguard_graph = build_graph()