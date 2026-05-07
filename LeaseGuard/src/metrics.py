"""
LeaseGuard — Metrics Engine
============================
Identical structure to LegislAI metrics.py — adapted field names.
Persists to data/metrics.json. Run metrics_report.py for resume bullets.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

METRICS_PATH = Path("data/metrics.json")

DEFAULT_METRICS: dict[str, Any] = {
    # Corpus
    "lease_chunks":         0,
    "law_chunks":           0,
    "states_ingested":      0,

    # Usage
    "total_queries":        0,
    "unique_states":        [],
    "task_distribution":    {
        "flag_risks": 0, "explain_clause": 0,
        "compare": 0, "rights": 0, "summary": 0,
    },

    # Retrieval
    "retrieval_strict_hits":    0,
    "retrieval_fallback_hits":  0,
    "total_chunks_retrieved":   0,
    "avg_chunks_per_query":     0.0,

    # Reliability
    "analysis_json_successes":  0,
    "analysis_json_failures":   0,
    "json_parse_success_rate":  0.0,

    # Latency
    "latency_records":      [],
    "p50_total_ms":         0,
    "p95_total_ms":         0,
    "avg_router_ms":        0,
    "avg_research_ms":      0,
    "avg_analysis_ms":      0,
    "avg_writer_ms":        0,

    # Web search
    "web_search_calls":     0,
    "web_search_successes": 0,
    "web_search_failures":  0,

    # Session
    "first_run":            None,
    "last_run":             None,
    "runs_today":           0,
    "last_run_date":        None,
}


def _load() -> dict[str, Any]:
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if METRICS_PATH.exists():
        try:
            with open(METRICS_PATH) as f:
                stored = json.load(f)
            for k, v in DEFAULT_METRICS.items():
                if k not in stored:
                    stored[k] = v
            return stored
        except Exception:
            pass
    return DEFAULT_METRICS.copy()


def _save(m: dict[str, Any]) -> None:
    tmp = METRICS_PATH.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(m, f, indent=2)
    tmp.replace(METRICS_PATH)


def _recompute(m: dict[str, Any]) -> None:
    total_parses = m["analysis_json_successes"] + m["analysis_json_failures"]
    m["json_parse_success_rate"] = round(
        m["analysis_json_successes"] / total_parses * 100, 1
    ) if total_parses > 0 else 0.0

    m["avg_chunks_per_query"] = round(
        m["total_chunks_retrieved"] / m["total_queries"], 1
    ) if m["total_queries"] > 0 else 0.0

    records = m["latency_records"][-200:]
    m["latency_records"] = records
    if records:
        totals = sorted(r["total_ms"] for r in records)
        n = len(totals)
        m["p50_total_ms"]    = totals[int(n * 0.50)]
        m["p95_total_ms"]    = totals[min(int(n * 0.95), n - 1)]
        m["avg_router_ms"]   = round(sum(r["router_ms"]   for r in records) / n)
        m["avg_research_ms"] = round(sum(r["research_ms"] for r in records) / n)
        m["avg_analysis_ms"] = round(sum(r["analysis_ms"] for r in records) / n)
        m["avg_writer_ms"]   = round(sum(r["writer_ms"]   for r in records) / n)

    m["unique_states"] = list(set(m["unique_states"]))


def record_query_start(task: str, states: list[str]) -> float:
    m = _load()
    m["total_queries"] += 1
    key = task if task in m["task_distribution"] else "flag_risks"
    m["task_distribution"][key] += 1
    m["unique_states"].extend(s for s in states if s)
    now   = datetime.now(timezone.utc).isoformat()
    today = datetime.now().strftime("%Y-%m-%d")
    if m["first_run"] is None:
        m["first_run"] = now
    m["last_run"] = now
    if m["last_run_date"] != today:
        m["runs_today"] = 0
        m["last_run_date"] = today
    m["runs_today"] += 1
    _recompute(m)
    _save(m)
    return time.time()


def record_retrieval(source: str, chunks_returned: int, used_fallback: bool) -> None:
    m = _load()
    m["total_chunks_retrieved"] += chunks_returned
    if used_fallback:
        m["retrieval_fallback_hits"] += 1
    else:
        m["retrieval_strict_hits"] += 1
    _recompute(m)
    _save(m)


def record_web_search(snippets_returned: int, success: bool) -> None:
    m = _load()
    m["web_search_calls"] += 1
    if success:
        m["web_search_successes"] += 1
    else:
        m["web_search_failures"] += 1
    _recompute(m)
    _save(m)


def record_analysis_parse(success: bool) -> None:
    m = _load()
    if success:
        m["analysis_json_successes"] += 1
    else:
        m["analysis_json_failures"] += 1
    _recompute(m)
    _save(m)


def record_latency(router_ms: int, research_ms: int, analysis_ms: int, writer_ms: int) -> None:
    m = _load()
    total = router_ms + research_ms + analysis_ms + writer_ms
    m["latency_records"].append({
        "ts":          datetime.now(timezone.utc).isoformat(),
        "router_ms":   router_ms,
        "research_ms": research_ms,
        "analysis_ms": analysis_ms,
        "writer_ms":   writer_ms,
        "total_ms":    total,
    })
    _recompute(m)
    _save(m)


def update_corpus_stats(lease_chunks: int, law_chunks: int, states_ingested: int) -> None:
    m = _load()
    m["lease_chunks"]    = lease_chunks
    m["law_chunks"]      = law_chunks
    m["states_ingested"] = states_ingested
    _recompute(m)
    _save(m)


def get_all() -> dict[str, Any]:
    m = _load()
    _recompute(m)
    return m


def get_resume_bullets() -> list[str]:
    m    = _load()
    runs = m["total_queries"]
    bullets = []

    if runs < 1:
        return ["Run the app and analyze a lease to generate metrics."]

    if m["law_chunks"] > 0:
        bullets.append(
            f"Built agentic RAG pipeline over {m['law_chunks']:,}-chunk ChromaDB corpus "
            f"spanning tenant law from {m['states_ingested']} US states, "
            f"enabling jurisdiction-specific lease clause analysis"
        )

    total_ret  = m["retrieval_strict_hits"] + m["retrieval_fallback_hits"]
    if total_ret >= 3:
        strict_pct = round(m["retrieval_strict_hits"] / total_ret * 100)
        bullets.append(
            f"Achieved {strict_pct}% strict metadata-filter retrieval hit rate "
            f"across {total_ret} ChromaDB queries using state-code metadata filtering"
        )

    if m["json_parse_success_rate"] > 0 and runs >= 3:
        bullets.append(
            f"Maintained {m['json_parse_success_rate']}% structured JSON extraction rate "
            f"from LLM analysis node across {runs} agent runs "
            f"using schema-enforced prompting"
        )

    if m["p95_total_ms"] > 0 and runs >= 3:
        bullets.append(
            f"End-to-end pipeline latency: p50={m['p50_total_ms']:,}ms, "
            f"p95={m['p95_total_ms']:,}ms across {runs} lease analyses "
            f"(Router {m['avg_router_ms']}ms · Research {m['avg_research_ms']}ms · "
            f"Analysis {m['avg_analysis_ms']}ms · Writer {m['avg_writer_ms']}ms)"
        )

    unique = len(set(m["unique_states"]))
    if unique >= 2:
        bullets.append(
            f"Analyzed leases across {unique} US states with jurisdiction-aware "
            f"retrieval cross-referencing uploaded lease text against state tenant law"
        )

    if m["web_search_calls"] >= 3:
        ws_rate = round(m["web_search_successes"] / m["web_search_calls"] * 100)
        bullets.append(
            f"Integrated Tavily web search with {ws_rate}% success rate "
            f"for real-time tenant rights enrichment across {m['web_search_calls']} queries"
        )

    return bullets