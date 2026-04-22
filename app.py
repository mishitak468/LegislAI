from src.agent import legislai_graph
import json
import os
import sys

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(__file__))


st.set_page_config(
    page_title="LegislAI | Agentic Policy Intelligence",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=JetBrains+Mono:wght@300;400;500;700&family=Lato:wght@300;400;700&display=swap');

/* ── Palette ──────────────────────────────────────────
   Background:  #1a1612  (warm charcoal, almost brown-black)
   Surface:     #221e19  (dark walnut)
   Border:      #3a3028  (muted bronze)
   Amber:       #e8a838  (primary accent — warm gold)
   Terracotta:  #c05a3a  (secondary accent — burnt sienna)
   Sage:        #6b9e6e  (tertiary — muted forest green)
   Text:        #f0e8d8  (warm cream)
   Muted:       #7a6e60  (warm gray)
──────────────────────────────────────────────────── */

html, body, [class*="css"] {
    font-family: 'Lato', sans-serif;
    color: #f0e8d8;
}

.main { background: #1a1612; }

section[data-testid="stSidebar"] {
    background: #1e1a15;
    border-right: 1px solid #3a3028;
}
section[data-testid="stSidebar"] * { color: #c8bfb0 !important; }
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4 { color: #f0e8d8 !important; }

textarea {
    background: #221e19 !important;
    border: 2px solid #3a3028 !important;
    border-radius: 6px !important;
    color: #f0e8d8 !important;
    font-size: 15px !important;
    font-family: 'Lato', sans-serif !important;
    padding: 16px !important;
    line-height: 1.7 !important;
}
textarea:focus {
    border-color: #e8a838 !important;
    box-shadow: 0 0 0 3px rgba(232,168,56,0.12) !important;
}

.stButton > button {
    background: #e8a838 !important;
    color: #1a1612 !important;
    border: none !important;
    border-radius: 4px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    letter-spacing: 0.1em !important;
    padding: 12px 32px !important;
    text-transform: uppercase !important;
    box-shadow: 0 2px 12px rgba(232,168,56,0.3) !important;
}
.stButton > button:hover {
    background: #f0b84a !important;
    box-shadow: 0 4px 20px rgba(232,168,56,0.45) !important;
}

div[data-baseweb="select"] > div {
    background: #221e19 !important;
    border: 1px solid #3a3028 !important;
    border-radius: 6px !important;
    color: #f0e8d8 !important;
}

div[data-testid="stMetric"] {
    background: #221e19;
    border: 1px solid #3a3028;
    border-top: 3px solid #e8a838;
    border-radius: 6px;
    padding: 20px 24px;
}
div[data-testid="stMetric"] label {
    color: #7a6e60 !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 0.14em !important;
    text-transform: uppercase !important;
    font-family: 'JetBrains Mono', monospace !important;
}
div[data-testid="stMetricValue"] {
    color: #f0e8d8 !important;
    font-family: 'DM Serif Display', serif !important;
    font-size: 20px !important;
}

div[data-testid="stExpander"] {
    background: #221e19;
    border: 1px solid #3a3028;
    border-radius: 6px;
}

div[data-testid="stDownloadButton"] > button {
    background: transparent !important;
    border: 1px solid #3a3028 !important;
    color: #7a6e60 !important;
    border-radius: 4px !important;
    font-size: 12px !important;
    font-family: 'JetBrains Mono', monospace !important;
}
div[data-testid="stDownloadButton"] > button:hover {
    border-color: #e8a838 !important;
    color: #e8a838 !important;
}

hr { border-color: #3a3028 !important; }

.hero-title {
    font-family: 'DM Serif Display', serif;
    font-size: 58px;
    font-style: italic;
    color: #f0e8d8;
    line-height: 1.05;
    margin-bottom: 6px;
    letter-spacing: -0.01em;
}
.hero-accent { color: #e8a838; font-style: normal; }
.hero-sub {
    color: #7a6e60;
    font-size: 13px;
    margin-bottom: 28px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    font-family: 'JetBrains Mono', monospace;
}

.node-card {
    background: #221e19;
    border: 1px solid #3a3028;
    border-left: 3px solid #3a3028;
    border-radius: 4px;
    padding: 14px 16px;
    margin-bottom: 8px;
}
.node-card.router   { border-left-color: #e8a838; }
.node-card.research { border-left-color: #6b9e6e; }
.node-card.analysis { border-left-color: #c05a3a; }
.node-card.writer   { border-left-color: #8fa8c8; }
.node-card-icon { font-size: 16px; margin-bottom: 3px; }
.node-card-title {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px; font-weight: 700;
    letter-spacing: 0.12em; text-transform: uppercase; margin-bottom: 4px;
}
.node-card.router   .node-card-title { color: #e8a838; }
.node-card.research .node-card-title { color: #6b9e6e; }
.node-card.analysis .node-card-title { color: #c05a3a; }
.node-card.writer   .node-card-title { color: #8fa8c8; }
.node-card-desc { color: #7a6e60; font-size: 11px; line-height: 1.5; }

.agent-step {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 11px 14px;
    border-radius: 4px;
    background: #221e19;
    border: 1px solid #3a3028;
    margin-bottom: 7px;
}
.agent-step.active { border-color: #e8a838; background: #261f10; }
.agent-step.done   { border-color: #6b9e6e; background: #1a211a; }

.step-dot { width: 10px; height: 10px; border-radius: 50%; margin-top: 3px; flex-shrink: 0; }
.step-active  { background: #e8a838; box-shadow: 0 0 7px #e8a83888; }
.step-done    { background: #6b9e6e; }
.step-pending { background: #3a3028; }

.step-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase;
    padding: 2px 6px; border-radius: 2px; margin-right: 7px;
}
.label-router   { background: #2e2410; color: #e8a838; }
.label-research { background: #1a2418; color: #6b9e6e; }
.label-analysis { background: #2a1810; color: #c05a3a; }
.label-writer   { background: #18202a; color: #8fa8c8; }
.step-text        { color: #7a6e60; font-size: 12px; font-family: 'JetBrains Mono', monospace; }
.step-text.active { color: #c8bfb0; }
.step-text.done   { color: #6b9e6e; }

.result-header {
    font-family: 'DM Serif Display', serif;
    font-style: italic;
    font-size: 28px; color: #f0e8d8; margin-bottom: 4px;
}
.result-meta {
    color: #7a6e60; font-size: 11px; margin-bottom: 18px;
    font-family: 'JetBrains Mono', monospace; letter-spacing: 0.05em;
}

.summary-box {
    background: #221e19;
    border: 1px solid #3a3028;
    border-left: 4px solid #e8a838;
    border-radius: 4px;
    padding: 22px 26px;
    color: #c8bfb0;
    font-size: 15px;
    line-height: 1.85;
    margin-bottom: 20px;
}
.memo-box {
    background: #221e19;
    border: 1px solid #3a3028;
    border-left: 4px solid #8fa8c8;
    border-radius: 4px;
    padding: 28px 32px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    line-height: 1.9;
    color: #c8bfb0;
    white-space: pre-wrap;
}
.tip-box {
    background: #221e19;
    border: 1px solid #3a3028;
    border-radius: 4px;
    padding: 14px 16px;
    color: #7a6e60;
    font-size: 12px;
    line-height: 1.7;
}
.tip-box strong { color: #c8bfb0; font-family: 'JetBrains Mono', monospace; font-size: 11px; letter-spacing: 0.06em; }

.vector-badge {
    background: #221e19;
    border: 1px solid #3a3028;
    border-top: 3px solid #e8a838;
    border-radius: 4px;
    padding: 16px;
    text-align: center;
}
.vector-badge .num {
    font-family: 'DM Serif Display', serif;
    font-size: 36px; color: #e8a838;
}
.vector-badge .lbl {
    color: #7a6e60; font-size: 10px; letter-spacing: 0.12em;
    text-transform: uppercase; font-family: 'JetBrains Mono', monospace;
}

.how-to-box {
    background: #221e19;
    border: 1px solid #3a3028;
    border-radius: 4px;
    padding: 28px 32px;
    margin-bottom: 28px;
}
</style>
""", unsafe_allow_html=True)


@st.cache_data
def load_catalog():
    path = "data/enriched_bills.json"
    if os.path.exists(path):
        with open(path) as f:
            data = json.load(f)
        data.sort(key=lambda x: int(x["bill_number"]))
        return {f"Bill {b['bill_number']}: {b['title'][:55]}...": b["bill_number"] for b in data}
    return {}


def step_html(label: str, lclass: str, text: str, status: str) -> str:
    dot = {"done": "step-done", "active": "step-active",
           "pending": "step-pending"}[status]
    card = {"done": "done", "active": "active", "pending": ""}[status]
    tclass = status
    return f"""<div class="agent-step {card}">
        <div class="step-dot {dot}"></div>
        <div><span class="step-label {lclass}">{label}</span>
        <span class="step-text {tclass}">{text}</span></div>
    </div>"""


bill_lookup = load_catalog()

with st.sidebar:
    st.markdown("""
    <div style="padding:8px 0 16px 0;">
        <div style="font-family:'DM Serif Display',serif;font-size:24px;font-style:italic;color:#f0e8d8;">
            ⚖️ Legis<span style="color:#e8a838;">AI</span>
        </div>
        <div style="color:#7a6e60;font-size:11px;margin-top:3px;font-family:'JetBrains Mono',monospace;letter-spacing:0.08em;">AGENTIC RAG · LANGGRAPH</div>
    </div>""", unsafe_allow_html=True)

    st.divider()

    st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:#7a6e60;margin-bottom:6px;">🤖 LLM Backend</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#7a6e60;font-size:11px;margin-bottom:8px;">Selects which AI model powers all 4 agent nodes. Gemini requires only a Google API key.</div>', unsafe_allow_html=True)
    model_choice = st.selectbox(
        "Model", options=["gemini", "claude", "gpt4o"],
        format_func=lambda m: {"gemini": "⚡ Gemini 2.5 Flash",
                               "claude": "🟠 Claude 3.5 Haiku", "gpt4o": "🟢 GPT-4o"}[m],
        label_visibility="collapsed",
    )

    st.divider()

    st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:#7a6e60;margin-bottom:6px;">📋 Quick-Select Bills</div>', unsafe_allow_html=True)
    st.markdown('<div style="color:#7a6e60;font-size:11px;margin-bottom:8px;">Pick up to 3 bills — auto-fills the query box below. You can still edit the query freely after selecting.</div>', unsafe_allow_html=True)

    if bill_lookup:
        quick_bills = st.multiselect(
            "Bills", options=list(bill_lookup.keys()),
            label_visibility="collapsed", max_selections=3, placeholder="Search bills…",
        )
    else:
        st.warning("⚠️ No bills found. Run `ingest_bills_async.py` first.")
        quick_bills = []

    st.divider()

    st.markdown('<div style="font-family:\'JetBrains Mono\',monospace;font-size:10px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:#7a6e60;margin-bottom:10px;">🔗 Agent Pipeline</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="node-card router">
        <div class="node-card-icon">🧭</div>
        <div class="node-card-title">1 · Router Node</div>
        <div class="node-card-desc">Reads your query. Extracts bill number(s) and decides: analyze, compare, or draft memo.</div>
    </div>
    <div class="node-card research">
        <div class="node-card-icon">🔍</div>
        <div class="node-card-title">2 · Research Node</div>
        <div class="node-card-desc">Pulls the top matching chunks from ChromaDB vector store + searches web via Tavily for current news.</div>
    </div>
    <div class="node-card analysis">
        <div class="node-card-icon">📊</div>
        <div class="node-card-title">3 · Analysis Node</div>
        <div class="node-card-desc">Scores each sector 1–5 for risk, maps impacted US states, runs head-to-head comparisons.</div>
    </div>
    <div class="node-card writer">
        <div class="node-card-icon">✍️</div>
        <div class="node-card-title">4 · Writer Node</div>
        <div class="node-card-desc">Produces a concise executive summary or a full formal policy memo based on your request.</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    try:
        from src.vector_db import get_vector_store
        db = get_vector_store()
        count = db._collection.count()
    except Exception:
        count = 0
    st.markdown(f"""
    <div class="vector-badge">
        <div class="num">{count:,}</div>
        <div class="lbl">chunks in vector store</div>
    </div>""", unsafe_allow_html=True)


st.markdown('<div class="hero-title">Policy<br><span class="hero-accent">Intelligence</span></div>',
            unsafe_allow_html=True)
st.markdown('<div class="hero-sub">4-node LangGraph agent &nbsp;·&nbsp; ChromaDB RAG &nbsp;·&nbsp; Live web search &nbsp;·&nbsp; Gemini / Claude / GPT-4o</div>', unsafe_allow_html=True)

# Query box
st.markdown("""
<div style="font-family:'DM Serif Display',serif;font-size:20px;font-style:italic;color:#f0e8d8;margin-bottom:4px;">
    What would you like to know?
</div>
<div style="color:#7a6e60;font-size:12px;margin-bottom:10px;font-family:'JetBrains Mono',monospace;letter-spacing:0.04em;">
    Write a question in plain English — include a bill number and the agent extracts it automatically.
</div>
""", unsafe_allow_html=True)

prefill = ""
if quick_bills:
    ids = [bill_lookup[b] for b in quick_bills]
    prefill = f"Analyze the impact of bill {ids[0]}" if len(
        ids) == 1 else f"Compare bills {' and '.join(ids)} across sectors and risk levels"

query = st.text_area(
    "query", value=prefill, height=150,
    label_visibility="collapsed",
    placeholder=(
        "Try one of these:\n"
        "  • Analyze the impact of bill 1234\n"
        "  • Compare bills 42 and 108 on healthcare and energy\n"
        "  • Draft a formal policy memo on bill 77"
    ),
)

# Tip cards
t1, t2, t3 = st.columns(3)
with t1:
    st.markdown("""<div class="tip-box">
        <strong>📌 Single Bill Analysis</strong><br>
        "Analyze the impact of bill 42"<br>
        → Risk scores, state map, executive summary
    </div>""", unsafe_allow_html=True)
with t2:
    st.markdown("""<div class="tip-box">
        <strong>⚖️ Bill Comparison</strong><br>
        "Compare bills 42 and 108"<br>
        → Head-to-head sector table, winner by risk
    </div>""", unsafe_allow_html=True)
with t3:
    st.markdown("""<div class="tip-box">
        <strong>📄 Policy Memo</strong><br>
        "Draft a policy memo on bill 77"<br>
        → Formal memo, downloadable as .txt
    </div>""", unsafe_allow_html=True)

st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
run_btn = st.button("▶ Run Agent — Analyze Now", type="primary")
st.divider()


if run_btn and query.strip():
    trace_col, result_col = st.columns([1, 2])

    with trace_col:
        st.markdown('<div style="font-family:\'DM Serif Display\',serif;font-style:italic;font-size:16px;color:#f0e8d8;margin-bottom:5px;">Agent Trace</div>', unsafe_allow_html=True)
        st.markdown('<div style="color:#7a6e60;font-size:11px;margin-bottom:12px;font-family:\'JetBrains Mono\',monospace;">Amber = running · Green = complete · Dark = waiting</div>', unsafe_allow_html=True)
        s_router = st.empty()
        s_research = st.empty()
        s_analysis = st.empty()
        s_writer = st.empty()
        s_router.markdown(step_html("Router",   "label-router",
                          "Parsing intent & bill IDs…", "active"), unsafe_allow_html=True)
        s_research.markdown(step_html("Research", "label-research",
                            "Waiting for router…",        "pending"), unsafe_allow_html=True)
        s_analysis.markdown(step_html("Analysis", "label-analysis",
                            "Waiting for research…",      "pending"), unsafe_allow_html=True)
        s_writer.markdown(step_html("Writer",   "label-writer",
                          "Waiting for analysis…",       "pending"), unsafe_allow_html=True)

    with result_col:
        placeholder = st.empty()
        placeholder.markdown("""
        <div style="background:#221e19;border:1px solid #3a3028;border-radius:4px;
                    padding:40px;text-align:center;">
            <div style="font-family:'DM Serif Display',serif;font-style:italic;font-size:20px;color:#e8a838;margin-bottom:8px;">Retrieving…</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:12px;color:#7a6e60;letter-spacing:0.06em;">QUERYING CHROMADB + WEB SEARCH</div>
        </div>""", unsafe_allow_html=True)

    config = {"configurable": {"model": model_choice}}
    initial_state = {
        "query": query, "task": "single", "bill_ids": [],
        "retrieved_chunks": {}, "web_snippets": {},
        "risk_scores": {}, "sectors": {}, "impacted_states": {},
        "comparison": None, "summary": "", "memo": None,
        "messages": [], "model_tag": model_choice,
    }

    final_state = {}
    try:
        for update in legislai_graph.stream(initial_state, config=config, stream_mode="updates"):
            for node_name, patch in update.items():
                if node_name == "router":
                    bids = patch.get("bill_ids", [])
                    tsk = patch.get("task", "single")
                    tlabel = {"single": "analyze", "compare": "compare",
                              "memo": "draft memo"}.get(tsk, tsk)
                    with trace_col:
                        s_router.markdown(step_html(
                            "Router", "label-router", f"Task: {tlabel} · Bills: {bids}", "done"), unsafe_allow_html=True)
                        s_research.markdown(step_html(
                            "Research", "label-research", "Querying ChromaDB + Tavily web search…", "active"), unsafe_allow_html=True)
                elif node_name == "research":
                    cc = sum(len(v) for v in patch.get(
                        "retrieved_chunks", {}).values())
                    wc = sum(len(v)
                             for v in patch.get("web_snippets", {}).values())
                    with trace_col:
                        s_research.markdown(step_html(
                            "Research", "label-research", f"{cc} chunks · {wc} web snippets", "done"), unsafe_allow_html=True)
                        s_analysis.markdown(step_html(
                            "Analysis", "label-analysis", "Scoring risk across sectors…", "active"), unsafe_allow_html=True)
                elif node_name == "analysis":
                    nb = len(patch.get("risk_scores", {}))
                    with trace_col:
                        s_analysis.markdown(step_html(
                            "Analysis", "label-analysis", f"{nb} bill(s) scored ✓", "done"), unsafe_allow_html=True)
                        s_writer.markdown(step_html(
                            "Writer", "label-writer", "Drafting output…", "active"), unsafe_allow_html=True)
                elif node_name == "writer":
                    with trace_col:
                        s_writer.markdown(step_html(
                            "Writer", "label-writer", "Complete ✓", "done"), unsafe_allow_html=True)
                final_state.update(patch)
    except Exception as e:
        placeholder.error(f"Agent error: {e}")
        st.stop()

    # Results
    with result_col:
        placeholder.empty()
        if not final_state.get("bill_ids"):
            st.warning("⚠️ No bill numbers found. Try: *'Analyze bill 42'*")
            st.stop()

        task = final_state.get("task", "single")
        bill_ids = final_state.get("bill_ids", [])
        label = {"single": f"📋 Impact Analysis · Bill {bill_ids[0]}", "compare": f"⚖️ Comparison · {' vs '.join(f'Bill {b}' for b in bill_ids)}", "memo": f"📄 Policy Memo · Bill {bill_ids[0]}"}.get(
            task, "Analysis")
        total_chunks = sum(len(v) for v in final_state.get(
            "retrieved_chunks", {}).values())

        st.markdown(
            f'<div class="result-header">{label}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="result-meta">Model: {model_choice} &nbsp;·&nbsp; {len(bill_ids)} bill(s) &nbsp;·&nbsp; {total_chunks} chunks retrieved</div>', unsafe_allow_html=True)

        if task == "memo" and final_state.get("memo"):
            st.markdown(
                f'<div class="memo-box">{final_state["memo"]}</div>', unsafe_allow_html=True)
            st.download_button("⬇ Download Policy Memo (.txt)", data=final_state["memo"],
                               file_name=f"memo_bill_{'_'.join(bill_ids)}.txt",
                               help="Save the full policy memo as a plain text file")
        else:
            if final_state.get("summary"):
                st.markdown(
                    f'<div class="summary-box">{final_state["summary"]}</div>', unsafe_allow_html=True)

            risk_scores = final_state.get("risk_scores", {})
            for bid, scores in risk_scores.items():
                if scores:
                    st.markdown(
                        f"**🔥 Sector Risk Index · Bill {bid}** &nbsp;<span style='color:#4a5280;font-size:12px;'>(1 = minimal risk → 5 = critical risk)</span>", unsafe_allow_html=True)
                    df = pd.DataFrame(list(scores.items()), columns=[
                                      "Sector", "Risk Score"])
                    fig = px.bar(df, x="Sector", y="Risk Score", color="Risk Score",
                                 color_continuous_scale=[[0, "#6b9e6e"], [0.5, "#e8a838"], [1, "#c05a3a"]], range_color=[1, 5])
                    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                                      plot_bgcolor="rgba(0,0,0,0)", margin={"r": 0, "t": 10, "l": 0, "b": 0},
                                      coloraxis_showscale=False, height=240,
                                      font=dict(
                                          family="JetBrains Mono", color="#7a6e60"),
                                      xaxis=dict(gridcolor="#3a3028"), yaxis=dict(gridcolor="#3a3028"))
                    fig.update_traces(marker_line_width=0)
                    st.plotly_chart(fig, use_container_width=True)

            comparison = final_state.get("comparison")
            if comparison and task == "compare":
                st.markdown("**📊 Head-to-Head Sector Comparison**")
                hth = comparison.get("head_to_head", {})
                if hth:
                    st.dataframe(pd.DataFrame(hth).T.rename_axis(
                        "Sector"), use_container_width=True)
                winner = comparison.get(
                    "winner") or comparison.get("lowest_risk_bill")
                if winner:
                    st.success(
                        f"✅ Bill {winner} carries the lowest overall risk across analyzed sectors.")
                if comparison.get("rationale"):
                    st.caption(comparison["rationale"])

            all_states = list(set(s for v in final_state.get(
                "impacted_states", {}).values() for s in v))
            if all_states:
                st.markdown(
                    "**📍 Impacted States** &nbsp;<span style='color:#4a5280;font-size:12px;'>(highlighted = state-specific clauses detected)</span>", unsafe_allow_html=True)
                fig = px.choropleth(locations=all_states, locationmode="USA-states", scope="usa",
                                    color=[1]*len(all_states), color_continuous_scale=[[0, "#1e1a4a"], [1, "#6c63ff"]])
                fig.update_layout(template="plotly_dark", margin={"r": 0, "t": 0, "l": 0, "b": 0},
                                  paper_bgcolor="rgba(0,0,0,0)", geo_bgcolor="rgba(0,0,0,0)",
                                  coloraxis_showscale=False, height=300)
                st.plotly_chart(fig, use_container_width=True)

        st.divider()
        with st.expander("🔍 View Agent Sources — What did the agent actually read?"):
            st.markdown('<div style="color:#7a6e60;font-size:12px;margin-bottom:10px;font-family:\'JetBrains Mono\',monospace;letter-spacing:0.03em;">These are the exact bill chunks and web articles the agent read. Grounding prevents hallucination — every claim traces to a real source.</div>', unsafe_allow_html=True)
            for bid in bill_ids:
                st.markdown(f"**📄 Bill {bid} — Vector Store Chunks**")
                for i, chunk in enumerate(final_state.get("retrieved_chunks", {}).get(bid, [])[:3]):
                    st.caption(f"Chunk {i+1}: {chunk[:300]}…")
                st.markdown(f"**🌐 Bill {bid} — Web Search Results**")
                for snip in final_state.get("web_snippets", {}).get(bid, [])[:2]:
                    st.caption(snip[:200])

        st.download_button("⬇ Export Full Report as JSON",
                           data=json.dumps(
                               {k: v for k, v in final_state.items() if k != "messages"}, indent=2),
                           file_name=f"legislai_report_{'_'.join(bill_ids)}.json",
                           help="Download the complete structured output from all 4 agent nodes as a JSON file")

elif run_btn:
    st.warning("⚠️ Please enter a query before running the agent.")

else:
    st.markdown("""
    <div class="how-to-box">
        <div style="font-family:'DM Serif Display',serif;font-style:italic;font-size:20px;color:#f0e8d8;margin-bottom:14px;">
            Getting Started
        </div>
        <div style="color:#7a6e60;font-size:14px;line-height:2.1;font-family:'Lato',sans-serif;">
            <b style="color:#e8a838;font-family:'JetBrains Mono',monospace;font-size:12px;">01.</b>&nbsp; Pick a bill from the sidebar, or type a bill number directly in the query box above.<br>
            <b style="color:#6b9e6e;font-family:'JetBrains Mono',monospace;font-size:12px;">02.</b>&nbsp; Choose your LLM backend — Gemini is the default and needs only a Google API key.<br>
            <b style="color:#c05a3a;font-family:'JetBrains Mono',monospace;font-size:12px;">03.</b>&nbsp; Click <b style="color:#e8a838;">▶ RUN AGENT</b> and watch the 4-node pipeline execute in real time.<br>
            <b style="color:#8fa8c8;font-family:'JetBrains Mono',monospace;font-size:12px;">04.</b>&nbsp; Download your report as JSON or a policy memo when the analysis is complete.
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🧭 Router Node", "Intent extraction",
                  help="Parses plain-English queries to identify task type (analyze/compare/memo) and bill number(s)")
    with c2:
        st.metric("🔍 Research Node", "RAG + Web search",
                  help="Retrieves top-6 matching chunks from ChromaDB vector store + live web results via Tavily API")
    with c3:
        st.metric("📊 Analysis Node", "Risk scoring",
                  help="Scores sectors 1–5, maps impacted US states, runs head-to-head comparison for multi-bill queries")
    with c4:
        st.metric("✍️ Writer Node", "Summary / Memo",
                  help="Writes a concise executive summary OR a full formal policy memo depending on your query")
