"""
LeaseGuard — Streamlit Frontend
================================
Upload your lease PDF, ask questions in plain English, get clause-by-clause
risk analysis grounded in your state's tenant law.
"""

from src.vector_db import (
    clear_lease_store,
    get_lease_store,
    get_law_store,
    law_chunk_count,
    lease_chunk_count,
)
from src.process_lease import process_lease_pdf
from src.metrics import update_corpus_stats
from src.agent import leaseguard_graph
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
    page_title="LeaseGuard | AI Lease Analyzer",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=JetBrains+Mono:wght@400;700&family=Lato:wght@300;400;700&display=swap');

html, body, [class*="css"] { font-family: 'Lato', sans-serif; color: #f0e8d8; }
.main { background: #1a1612; }
section[data-testid="stSidebar"] { background: #1e1a15; border-right: 1px solid #3a3028; }
section[data-testid="stSidebar"] * { color: #c8bfb0 !important; }

textarea {
    background: #221e19 !important; border: 2px solid #3a3028 !important;
    border-radius: 6px !important; color: #f0e8d8 !important;
    font-size: 15px !important; padding: 14px !important; line-height: 1.7 !important;
}
textarea:focus { border-color: #e8a838 !important; }

.stButton > button {
    background: #e8a838 !important; color: #1a1612 !important; border: none !important;
    border-radius: 4px !important; font-family: 'JetBrains Mono', monospace !important;
    font-weight: 700 !important; font-size: 13px !important; letter-spacing: 0.1em !important;
    padding: 10px 28px !important; text-transform: uppercase !important;
}

div[data-baseweb="select"] > div {
    background: #221e19 !important; border: 1px solid #3a3028 !important;
    border-radius: 6px !important; color: #f0e8d8 !important;
}

div[data-testid="stMetric"] {
    background: #221e19; border: 1px solid #3a3028;
    border-top: 3px solid #e8a838; border-radius: 6px; padding: 16px 20px;
}
div[data-testid="stMetric"] label {
    color: #7a6e60 !important; font-size: 10px !important; font-weight: 700 !important;
    letter-spacing: 0.14em !important; text-transform: uppercase !important;
    font-family: 'JetBrains Mono', monospace !important;
}
div[data-testid="stMetricValue"] {
    color: #f0e8d8 !important; font-family: 'DM Serif Display', serif !important; font-size: 20px !important;
}

div[data-testid="stExpander"] { background: #221e19; border: 1px solid #3a3028; border-radius: 6px; }
div[data-testid="stDownloadButton"] > button {
    background: transparent !important; border: 1px solid #3a3028 !important;
    color: #7a6e60 !important; border-radius: 4px !important; font-size: 12px !important;
}
div[data-testid="stDownloadButton"] > button:hover { border-color: #e8a838 !important; color: #e8a838 !important; }
hr { border-color: #3a3028 !important; }

.hero-title {
    font-family: 'DM Serif Display', serif; font-size: 50px; font-style: italic;
    color: #f0e8d8; line-height: 1.05; margin-bottom: 6px;
}
.hero-accent { color: #e8a838; font-style: normal; }
.hero-sub {
    color: #7a6e60; font-size: 13px; margin-bottom: 24px;
    letter-spacing: 0.12em; text-transform: uppercase; font-family: 'JetBrains Mono', monospace;
}

.disclaimer {
    background: #2a1810; border: 1px solid #c05a3a; border-radius: 4px;
    padding: 10px 16px; font-size: 12px; color: #e8a060;
    font-family: 'JetBrains Mono', monospace; margin-bottom: 20px;
}

.risk-card {
    background: #221e19; border: 1px solid #3a3028; border-left: 4px solid;
    border-radius: 4px; padding: 16px 18px; margin-bottom: 10px;
}
.risk-card.r5 { border-left-color: #c05a3a; }
.risk-card.r4 { border-left-color: #e8a838; }
.risk-card.r3 { border-left-color: #d4a84b; }
.risk-card.r2 { border-left-color: #6b9e6e; }
.risk-card.r1 { border-left-color: #4a7a4d; }

.risk-clause {
    font-family: 'JetBrains Mono', monospace; font-size: 12px;
    color: #c8bfb0; margin-bottom: 6px; font-style: italic;
}
.risk-reason { font-size: 13px; color: #a8a098; line-height: 1.5; margin-bottom: 6px; }
.risk-tip {
    font-size: 12px; color: #6b9e6e; font-family: 'JetBrains Mono', monospace;
    padding-top: 6px; border-top: 1px solid #3a3028;
}
.risk-badge {
    font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700;
    padding: 2px 8px; border-radius: 3px; letter-spacing: 0.08em; float: right;
}
.badge-5 { background: #2a1410; color: #c05a3a; }
.badge-4 { background: #2a2010; color: #e8a838; }
.badge-3 { background: #252010; color: #d4a84b; }
.badge-2 { background: #1a2418; color: #6b9e6e; }
.badge-1 { background: #182418; color: #4a7a4d; }

.illegal-card {
    background: #2a1410; border: 1px solid #c05a3a; border-radius: 4px;
    padding: 12px 16px; margin-bottom: 8px;
    font-size: 13px; color: #e8a060; line-height: 1.5;
}

.rights-card {
    background: #1a211a; border: 1px solid #6b9e6e; border-radius: 4px;
    padding: 12px 16px; margin-bottom: 8px;
    font-size: 13px; color: #a8c8a8; line-height: 1.5;
}

.summary-box {
    background: #221e19; border: 1px solid #3a3028; border-left: 4px solid #e8a838;
    border-radius: 4px; padding: 20px 24px; color: #c8bfb0;
    font-size: 15px; line-height: 1.85; margin-bottom: 20px;
}

.tip-box {
    background: #221e19; border: 1px solid #3a3028; border-radius: 4px;
    padding: 12px 16px; color: #7a6e60; font-size: 12px; line-height: 1.7;
}
.tip-box strong { color: #c8bfb0; font-family: 'JetBrains Mono', monospace; font-size: 11px; }

.agent-step {
    display: flex; align-items: flex-start; gap: 12px; padding: 10px 14px;
    border-radius: 4px; background: #221e19; border: 1px solid #3a3028; margin-bottom: 7px;
}
.agent-step.active { border-color: #e8a838; background: #261f10; }
.agent-step.done   { border-color: #6b9e6e; background: #1a211a; }
.step-dot { width: 10px; height: 10px; border-radius: 50%; margin-top: 3px; flex-shrink: 0; }
.step-active  { background: #e8a838; }
.step-done    { background: #6b9e6e; }
.step-pending { background: #3a3028; }
.step-label {
    font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700;
    letter-spacing: 0.1em; text-transform: uppercase; padding: 2px 6px; border-radius: 2px; margin-right: 7px;
}
.label-router   { background: #2e2410; color: #e8a838; }
.label-research { background: #1a2418; color: #6b9e6e; }
.label-analysis { background: #2a1810; color: #c05a3a; }
.label-writer   { background: #18202a; color: #8fa8c8; }
.step-text        { color: #7a6e60; font-size: 12px; font-family: 'JetBrains Mono', monospace; }
.step-text.active { color: #c8bfb0; }
.step-text.done   { color: #6b9e6e; }

.sec-label {
    font-family: 'JetBrains Mono', monospace; font-size: 10px; font-weight: 700;
    letter-spacing: 0.14em; text-transform: uppercase; color: #7a6e60; margin-bottom: 10px;
}
.upload-prompt {
    background: #221e19; border: 2px dashed #3a3028; border-radius: 6px;
    padding: 32px; text-align: center; color: #7a6e60; margin-bottom: 20px;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

RISK_LABELS = {5: "RED FLAG", 4: "PUSH BACK",
               3: "WATCH THIS", 2: "MINOR", 1: "STANDARD"}
RISK_COLORS = {5: "#c05a3a", 4: "#e8a838",
               3: "#d4a84b", 2: "#6b9e6e", 1: "#4a7a4d"}

LEGISLATIVE_KEYWORDS = {
    "lease", "rent", "landlord", "tenant", "clause", "deposit", "eviction",
    "sublease", "subletting", "renewal", "termination", "maintenance", "repairs",
    "entry", "notice", "agreement", "apartment", "unit", "property", "fee",
    "penalty", "pet", "parking", "utilities", "illegal", "rights", "law",
    "explain", "summarize", "compare", "flag", "risk",
}


def looks_like_query(q: str) -> bool:
    words = q.lower().split()
    return len(words) >= 2 and any(w.strip(".,;:!?") in LEGISLATIVE_KEYWORDS for w in words)


def step_html(label, lclass, text, status):
    dot = {"done": "step-done", "active": "step-active",
           "pending": "step-pending"}[status]
    card = {"done": "done", "active": "active", "pending": ""}[status]
    return f"""<div class="agent-step {card}">
        <div class="step-dot {dot}"></div>
        <div><span class="step-label {lclass}">{label}</span>
        <span class="step-text {status}">{text}</span></div>
    </div>"""


def badge(risk: int) -> str:
    return f'<span class="risk-badge badge-{risk}">{RISK_LABELS.get(risk,"?")}</span>'


def risk_card_html(fc: dict) -> str:
    risk = int(fc.get("risk", 3))
    level = f"r{risk}"
    return f"""<div class="risk-card {level}">
        {badge(risk)}
        <div class="risk-clause">"{fc.get('clause','')}"</div>
        <div class="risk-reason">{fc.get('reason','')}</div>
        <div class="risk-tip">💡 {fc.get('negotiate','')}</div>
    </div>"""


def ingest_lease(file) -> int:
    """Process uploaded PDF and load into ChromaDB. Returns chunk count."""
    clear_lease_store()
    chunks = process_lease_pdf(file)
    if not chunks:
        return 0
    db = get_lease_store()
    texts = [c["text"] for c in chunks]
    metas = [c["metadata"] for c in chunks]
    ids = [f"lease_{i}" for i in range(len(chunks))]
    db.add_texts(texts=texts, metadatas=metas, ids=ids)
    return len(chunks)


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
    <div style="padding:8px 0 16px 0;">
        <div style="font-family:'DM Serif Display',serif;font-size:22px;font-style:italic;color:#f0e8d8;">
            🏠 Lease<span style="color:#e8a838;">Guard</span>
        </div>
        <div style="color:#7a6e60;font-size:11px;margin-top:2px;font-family:'JetBrains Mono',monospace;
                    letter-spacing:0.08em;">AGENTIC LEASE ANALYSIS · LANGGRAPH</div>
    </div>""", unsafe_allow_html=True)

    st.divider()

    # Upload
    st.markdown('<div class="sec-label">📄 Upload Your Lease</div>',
                unsafe_allow_html=True)
    st.markdown('<div style="color:#7a6e60;font-size:11px;margin-bottom:8px;">PDF only. Your document stays local — nothing is stored after your session.</div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader(
        "lease", type=["pdf"], label_visibility="collapsed",
        help="Upload your rental agreement or lease PDF"
    )

    if uploaded_file:
        with st.spinner("Reading lease…"):
            n_chunks = ingest_lease(uploaded_file)
        if n_chunks > 0:
            st.success(f"✅ {n_chunks} chunks loaded from lease")
            st.session_state["lease_loaded"] = True
            st.session_state["lease_name"] = uploaded_file.name
        else:
            st.error("Could not extract text from this PDF.")
            st.session_state["lease_loaded"] = False
    else:
        st.session_state.setdefault("lease_loaded", False)

    st.divider()

    # State selector
    st.markdown('<div class="sec-label">📍 Your State</div>',
                unsafe_allow_html=True)
    st.markdown('<div style="color:#7a6e60;font-size:11px;margin-bottom:8px;">Sets which state\'s tenant law is used to check your lease.</div>', unsafe_allow_html=True)

    US_STATES = ["", "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
                 "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS", "MO",
                 "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA",
                 "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"]
    state_choice = st.selectbox(
        "state", options=US_STATES,
        format_func=lambda s: "Select your state…" if s == "" else s,
        label_visibility="collapsed",
    )

    st.divider()

    # Model
    st.markdown('<div class="sec-label">🤖 LLM Backend</div>',
                unsafe_allow_html=True)
    model_choice = st.selectbox(
        "Model", options=["gemini", "claude", "gpt4o"],
        format_func=lambda m: {"gemini": "⚡ Gemini 2.5 Flash",
                               "claude": "🟠 Claude 3.5 Haiku", "gpt4o": "🟢 GPT-4o"}[m],
        label_visibility="collapsed",
    )

    st.divider()

    # Agent pipeline cards
    st.markdown('<div class="sec-label">🔗 How It Works</div>',
                unsafe_allow_html=True)
    st.markdown("""
    <div style="background:#221e19;border:1px solid #3a3028;border-left:3px solid #e8a838;
                border-radius:4px;padding:12px 14px;margin-bottom:8px;">
        <div style="font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;
                    color:#e8a838;letter-spacing:0.1em;margin-bottom:4px;">1 · ROUTER</div>
        <div style="color:#7a6e60;font-size:11px;">Detects task — flag risks, explain clause, know your rights, or summarize.</div>
    </div>
    <div style="background:#221e19;border:1px solid #3a3028;border-left:3px solid #6b9e6e;
                border-radius:4px;padding:12px 14px;margin-bottom:8px;">
        <div style="font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;
                    color:#6b9e6e;letter-spacing:0.1em;margin-bottom:4px;">2 · RESEARCH</div>
        <div style="color:#7a6e60;font-size:11px;">Retrieves your lease chunks + your state's tenant law + live web results.</div>
    </div>
    <div style="background:#221e19;border:1px solid #3a3028;border-left:3px solid #c05a3a;
                border-radius:4px;padding:12px 14px;margin-bottom:8px;">
        <div style="font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;
                    color:#c05a3a;letter-spacing:0.1em;margin-bottom:4px;">3 · ANALYSIS</div>
        <div style="color:#7a6e60;font-size:11px;">Scores each clause category 1–5, flags risky clauses, identifies illegal terms.</div>
    </div>
    <div style="background:#221e19;border:1px solid #3a3028;border-left:3px solid #8fa8c8;
                border-radius:4px;padding:12px 14px;margin-bottom:8px;">
        <div style="font-family:'JetBrains Mono',monospace;font-size:10px;font-weight:700;
                    color:#8fa8c8;letter-spacing:0.1em;margin-bottom:4px;">4 · WRITER</div>
        <div style="color:#7a6e60;font-size:11px;">Plain-English summary with specific negotiation tips — no jargon.</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Corpus stats
    lc = lease_chunk_count()
    lwc = law_chunk_count()
    update_corpus_stats(lc, lwc, 0)
    st.markdown(f"""
    <div style="background:#221e19;border:1px solid #3a3028;border-top:3px solid #e8a838;
                border-radius:4px;padding:12px;text-align:center;margin-bottom:8px;">
        <div style="font-family:'DM Serif Display',serif;font-size:26px;color:#e8a838;">{lc}</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#7a6e60;
                    letter-spacing:0.08em;text-transform:uppercase;">lease chunks loaded</div>
    </div>
    <div style="background:#221e19;border:1px solid #3a3028;border-top:3px solid #6b9e6e;
                border-radius:4px;padding:12px;text-align:center;">
        <div style="font-family:'DM Serif Display',serif;font-size:26px;color:#6b9e6e;">{lwc:,}</div>
        <div style="font-family:'JetBrains Mono',monospace;font-size:10px;color:#7a6e60;
                    letter-spacing:0.08em;text-transform:uppercase;">state law chunks</div>
    </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

st.markdown('<div class="hero-title">Know Your<br><span class="hero-accent">Lease</span></div>',
            unsafe_allow_html=True)
st.markdown('<div class="hero-sub">4-node LangGraph agent · PDF ingestion · State tenant law · No jargon</div>', unsafe_allow_html=True)

st.markdown('<div class="disclaimer">⚠️ LeaseGuard is not a law firm and does not provide legal advice. Analysis is for informational purposes only. Consult a licensed attorney before making decisions about your lease.</div>', unsafe_allow_html=True)

# Query box
st.markdown("""
<div style="font-family:'DM Serif Display',serif;font-size:18px;font-style:italic;
            color:#f0e8d8;margin-bottom:4px;">Ask anything about your lease</div>
<div style="color:#7a6e60;font-size:12px;margin-bottom:10px;font-family:'JetBrains Mono',
            monospace;letter-spacing:0.03em;">
    Upload your lease in the sidebar first. Then ask in plain English.
</div>
""", unsafe_allow_html=True)

t1, t2, t3 = st.columns(3)
with t1:
    st.markdown("""<div class="tip-box"><strong>🚩 FLAG RISKS</strong><br>
    "Flag all the risky clauses in my lease"<br>→ Clause-by-clause risk scores</div>""", unsafe_allow_html=True)
with t2:
    st.markdown("""<div class="tip-box"><strong>⚖️ KNOW YOUR RIGHTS</strong><br>
    "What are my rights if my landlord enters without notice in NY?"<br>→ State law answer</div>""", unsafe_allow_html=True)
with t3:
    st.markdown("""<div class="tip-box"><strong>💬 EXPLAIN A CLAUSE</strong><br>
    "What does the automatic renewal clause mean?"<br>→ Plain English explanation</div>""", unsafe_allow_html=True)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

query = st.text_area(
    "query", height=120, label_visibility="collapsed",
    placeholder=(
        "Try:\n"
        "  • Flag all risky clauses in my lease\n"
        "  • What does the early termination fee clause mean?\n"
        "  • Is the landlord allowed to enter without 24 hours notice in California?\n"
        "  • Summarize my lease in plain English"
    ),
)

run_btn = st.button("▶ Analyze Lease", type="primary")
st.divider()


# ─────────────────────────────────────────────
# EXECUTION
# ─────────────────────────────────────────────

if run_btn and query.strip():
    if not st.session_state.get("lease_loaded"):
        st.warning("⚠️ Please upload your lease PDF in the sidebar first.")
        st.stop()

    if not looks_like_query(query):
        st.warning(
            "⚠️ That doesn't look like a lease question. Try: *'Flag all risky clauses in my lease'*")
        st.stop()

    trace_col, result_col = st.columns([1, 2])

    with trace_col:
        st.markdown('<div style="font-family:\'DM Serif Display\',serif;font-style:italic;font-size:15px;color:#f0e8d8;margin-bottom:4px;">Agent Trace</div>', unsafe_allow_html=True)
        st.markdown('<div style="color:#7a6e60;font-size:11px;font-family:\'JetBrains Mono\',monospace;margin-bottom:10px;">Amber = running · Green = done</div>', unsafe_allow_html=True)
        s_router = st.empty()
        s_research = st.empty()
        s_analysis = st.empty()
        s_writer = st.empty()
        s_router.markdown(step_html("Router",   "label-router",
                          "Detecting task…",     "active"), unsafe_allow_html=True)
        s_research.markdown(step_html("Research", "label-research",
                            "Waiting…",            "pending"), unsafe_allow_html=True)
        s_analysis.markdown(step_html("Analysis", "label-analysis",
                            "Waiting…",            "pending"), unsafe_allow_html=True)
        s_writer.markdown(step_html("Writer",   "label-writer",
                          "Waiting…",            "pending"), unsafe_allow_html=True)

    with result_col:
        placeholder = st.empty()
        placeholder.markdown("""
        <div style="background:#221e19;border:1px solid #3a3028;border-radius:4px;
                    padding:36px;text-align:center;">
            <div style="font-family:'DM Serif Display',serif;font-style:italic;
                        font-size:17px;color:#e8a838;margin-bottom:6px;">Analyzing your lease…</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:11px;
                        color:#7a6e60;letter-spacing:0.06em;">RETRIEVING LEASE + STATE LAW</div>
        </div>""", unsafe_allow_html=True)

    config = {"configurable": {"model": model_choice}}
    initial_state = {
        "query":           query,
        "state_code":      state_choice,
        "task":            "flag_risks",
        "lease_chunks":    [],
        "law_chunks":      [],
        "web_snippets":    [],
        "risk_scores":     {},
        "flagged_clauses": [],
        "illegal_clauses": [],
        "tenant_rights":   [],
        "summary":         "",
        "negotiation_tips": [],
        "disclaimer":      "",
        "messages":        [],
        "model_tag":       model_choice,
        "t_router_ms":     0,
        "t_research_ms":   0,
        "t_analysis_ms":   0,
        "t_writer_ms":     0,
    }

    final_state = {}
    try:
        for update in leaseguard_graph.stream(initial_state, config=config, stream_mode="updates"):
            for node_name, patch in update.items():
                if node_name == "router":
                    tsk = patch.get("task", "flag_risks")
                    sc = patch.get("state_code", "") or "unknown"
                    with trace_col:
                        s_router.markdown(step_html(
                            "Router", "label-router", f"Task: {tsk} · State: {sc}", "done"), unsafe_allow_html=True)
                        s_research.markdown(step_html(
                            "Research", "label-research", "Retrieving lease + law chunks…", "active"), unsafe_allow_html=True)
                elif node_name == "research":
                    lc = len(patch.get("lease_chunks", []))
                    lwc = len(patch.get("law_chunks", []))
                    with trace_col:
                        s_research.markdown(step_html(
                            "Research", "label-research", f"{lc} lease chunks · {lwc} law chunks", "done"), unsafe_allow_html=True)
                        s_analysis.markdown(step_html(
                            "Analysis", "label-analysis", "Scoring clause risks…", "active"), unsafe_allow_html=True)
                elif node_name == "analysis":
                    nf = len(patch.get("flagged_clauses", []))
                    with trace_col:
                        s_analysis.markdown(step_html(
                            "Analysis", "label-analysis", f"{nf} clauses flagged ✓", "done"), unsafe_allow_html=True)
                        s_writer.markdown(step_html(
                            "Writer", "label-writer", "Writing plain-English summary…", "active"), unsafe_allow_html=True)
                elif node_name == "writer":
                    with trace_col:
                        s_writer.markdown(step_html(
                            "Writer", "label-writer", "Complete ✓", "done"), unsafe_allow_html=True)
                final_state.update(patch)
    except Exception as e:
        placeholder.error(f"Agent error: {e}")
        st.stop()

    # ── RESULTS ───────────────────────────────────────────────────────────────
    with result_col:
        placeholder.empty()

        state_label = f" · {final_state.get('state_code','')}" if final_state.get(
            "state_code") else ""
        lease_name = st.session_state.get("lease_name", "your lease")
        st.markdown(
            f'<div style="font-family:\'DM Serif Display\',serif;font-style:italic;font-size:22px;color:#f0e8d8;margin-bottom:4px;">Analysis — {lease_name}{state_label}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="color:#7a6e60;font-size:11px;font-family:\'JetBrains Mono\',monospace;margin-bottom:16px;">Model: {model_choice} · {len(final_state.get("lease_chunks",[]))} lease chunks · {len(final_state.get("law_chunks",[]))} law chunks</div>', unsafe_allow_html=True)

        # Disclaimer
        if final_state.get("disclaimer"):
            st.markdown(
                f'<div class="disclaimer">{final_state["disclaimer"]}</div>', unsafe_allow_html=True)

        # Summary
        if final_state.get("summary"):
            st.markdown(
                f'<div class="summary-box">{final_state["summary"]}</div>', unsafe_allow_html=True)

        # Risk score bar chart
        risk_scores = final_state.get("risk_scores", {})
        if risk_scores:
            st.markdown("**🔥 Clause Risk Index** &nbsp;<span style='color:#7a6e60;font-size:11px;font-family:JetBrains Mono,monospace;'>(1=standard · 5=red flag)</span>", unsafe_allow_html=True)
            df = pd.DataFrame(list(risk_scores.items()),
                              columns=["Category", "Risk Score"])
            df = df.sort_values("Risk Score", ascending=False)
            fig = px.bar(df, x="Category", y="Risk Score", color="Risk Score",
                         color_continuous_scale=[[0, "#4a7a4d"], [0.4, "#e8a838"], [1, "#c05a3a"]], range_color=[1, 5])
            fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)",
                              plot_bgcolor="rgba(0,0,0,0)", margin={"r": 0, "t": 10, "l": 0, "b": 0},
                              coloraxis_showscale=False, height=230,
                              font=dict(family="JetBrains Mono",
                                        color="#7a6e60"),
                              xaxis=dict(gridcolor="#3a3028", tickangle=-30),
                              yaxis=dict(gridcolor="#3a3028", range=[0, 5.5]))
            fig.update_traces(marker_line_width=0)
            st.plotly_chart(fig, use_container_width=True, key="risk_bar")

        # Flagged clauses
        flagged = final_state.get("flagged_clauses", [])
        if flagged:
            st.markdown("**🚩 Flagged Clauses — Ranked by Risk**")
            sorted_flagged = sorted(
                flagged, key=lambda x: x.get("risk", 0), reverse=True)
            for fc in sorted_flagged:
                st.markdown(risk_card_html(fc), unsafe_allow_html=True)

        # Illegal clauses
        illegal = final_state.get("illegal_clauses", [])
        if illegal:
            st.markdown("**🚫 Potentially Illegal Clauses**")
            for item in illegal:
                st.markdown(
                    f'<div class="illegal-card">⛔ {item}</div>', unsafe_allow_html=True)

        # Tenant rights
        rights = final_state.get("tenant_rights", [])
        if rights:
            st.markdown(
                f"**✅ Your Rights{' in ' + final_state.get('state_code','') if final_state.get('state_code') else ''}**")
            for r in rights:
                st.markdown(
                    f'<div class="rights-card">✓ {r}</div>', unsafe_allow_html=True)

        # Negotiation tips
        tips = final_state.get("negotiation_tips", [])
        if tips:
            st.divider()
            st.markdown("**💡 What to Negotiate**")
            for tip in tips:
                st.markdown(f"- {tip}")

        st.divider()

        with st.expander("🔍 Source Context — What the agent read"):
            st.markdown('<div style="color:#7a6e60;font-size:11px;font-family:\'JetBrains Mono\',monospace;margin-bottom:10px;">Every finding traces to one of these retrieved chunks — no hallucination.</div>', unsafe_allow_html=True)
            st.markdown("**📄 Lease Chunks**")
            for i, chunk in enumerate(final_state.get("lease_chunks", [])[:3]):
                st.caption(f"Chunk {i+1}: {chunk[:300]}…")
            st.markdown("**⚖️ State Law Chunks**")
            for i, chunk in enumerate(final_state.get("law_chunks", [])[:2]):
                st.caption(f"Law {i+1}: {chunk[:300]}…")

        st.download_button("⬇ Export Full Analysis as JSON",
                           data=json.dumps(
                               {k: v for k, v in final_state.items() if k != "messages"}, indent=2),
                           file_name=f"leaseguard_analysis.json")

elif run_btn:
    st.warning("⚠️ Please enter a question about your lease.")

else:
    st.markdown("""
    <div style="background:#221e19;border:1px solid #3a3028;border-radius:4px;
                padding:24px 28px;margin-bottom:24px;">
        <div style="font-family:'DM Serif Display',serif;font-style:italic;font-size:18px;
                    color:#f0e8d8;margin-bottom:12px;">How to use LeaseGuard</div>
        <div style="color:#7a6e60;font-size:14px;line-height:2.1;">
            <b style="color:#e8a838;font-family:'JetBrains Mono',monospace;font-size:11px;">01.</b>&nbsp;
                Upload your lease PDF in the sidebar — nothing leaves your machine.<br>
            <b style="color:#6b9e6e;font-family:'JetBrains Mono',monospace;font-size:11px;">02.</b>&nbsp;
                Select your state so the agent can check clauses against local law.<br>
            <b style="color:#c05a3a;font-family:'JetBrains Mono',monospace;font-size:11px;">03.</b>&nbsp;
                Ask anything in plain English — the agent reads your actual lease, not a template.<br>
            <b style="color:#8fa8c8;font-family:'JetBrains Mono',monospace;font-size:11px;">04.</b>&nbsp;
                Get clause-by-clause risk scores, flagged terms, and specific negotiation tips.
        </div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🧭 Router",   "Task detection",
                  help="Detects: flag risks / explain clause / know rights / summarize")
    with c2:
        st.metric("🔍 Research", "Lease + Law + Web",
                  help="Your PDF chunks + state tenant law + live Tavily search")
    with c3:
        st.metric("📊 Analysis", "Clause risk 1–5",
                  help="Schema-enforced JSON: risk scores, flagged clauses, illegal terms")
    with c4:
        st.metric("✍️ Writer",   "Plain English",
                  help="No jargon — specific quotes, reasons, and negotiation tips")
