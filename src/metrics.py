from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

METRICS_PATH = Path("data/metrics.json")


DEFAULT_METRICS: dict[str, Any] = {
    "total_chunks": 0,
    "bills_ingested": 0,
    "avg_chunks_per_bill": 0.0,

    "total_queries": 0,
    "unique_bills_analyzed": [],
    "task_distribution": {
        "single": 0,
        "compare": 0,
        "memo": 0,
        "unknown": 0,
    },

    "retrieval_strict_hits": 0,
    "retrieval_fallback_hits": 0,
    "total_chunks_retrieved": 0,
    "avg_chunks_per_query": 0.0,

    "analysis_json_successes": 0,
    "analysis_json_failures": 0,
    "json_parse_success_rate": 0.0,


    "latency_records": [],
    "p50_total_ms": 0,
    "p95_total_ms": 0,
    "avg_router_ms": 0,
    "avg_research_ms": 0,
    "avg_analysis_ms": 0,
    "avg_writer_ms": 0,

    "web_search_calls": 0,
    "web_search_successes": 0,
    "web_search_failures": 0,
    "avg_snippets_per_bill": 0.0,

    "first_run": None,
    "last_run": None,
    "runs_today": 0,
    "last_run_date": None,
}


def _load() -> dict[str, Any]:
    METRICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    if METRICS_PATH.exists():
        try:
            with open(METRICS_PATH) as f:
                stored = json.load(f)
            # Forward-fill any new keys added since last run
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
    """Recompute all derived fields in-place after any mutation."""
    total_parses = m["analysis_json_successes"] + m["analysis_json_failures"]
    m["json_parse_success_rate"] = round(
        m["analysis_json_successes"] / total_parses * 100, 1
    ) if total_parses > 0 else 0.0

    m["avg_chunks_per_query"] = round(
        m["total_chunks_retrieved"] / m["total_queries"], 1
    ) if m["total_queries"] > 0 else 0.0

    total_web_calls = m["web_search_calls"]
    if total_web_calls > 0:
        pass

    records = m["latency_records"][-200:]  # keep last 200
    m["latency_records"] = records
    if records:
        totals = sorted(r["total_ms"] for r in records)
        n = len(totals)
        m["p50_total_ms"] = totals[int(n * 0.50)]
        m["p95_total_ms"] = totals[min(int(n * 0.95), n - 1)]
        m["avg_router_ms"] = round(sum(r["router_ms"] for r in records) / n)
        m["avg_research_ms"] = round(
            sum(r["research_ms"] for r in records) / n)
        m["avg_analysis_ms"] = round(
            sum(r["analysis_ms"] for r in records) / n)
        m["avg_writer_ms"] = round(sum(r["writer_ms"] for r in records) / n)

    if m["bills_ingested"] > 0:
        m["avg_chunks_per_bill"] = round(
            m["total_chunks"] / m["bills_ingested"], 1)

    m["unique_bills_analyzed"] = list(set(m["unique_bills_analyzed"]))


def record_query_start(task: str, bill_ids: list[str]) -> float:
    """Call at query start. Returns start timestamp."""
    m = _load()
    m["total_queries"] += 1
    m["task_distribution"][task if task in m["task_distribution"] else "unknown"] += 1
    m["unique_bills_analyzed"].extend(bill_ids)

    now = datetime.now(timezone.utc).isoformat()
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


def record_retrieval(bill_id: str, chunks_returned: int, used_fallback: bool) -> None:
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


def record_latency(
    router_ms: int,
    research_ms: int,
    analysis_ms: int,
    writer_ms: int,
) -> None:
    m = _load()
    total = router_ms + research_ms + analysis_ms + writer_ms
    m["latency_records"].append({
        "ts": datetime.now(timezone.utc).isoformat(),
        "router_ms": router_ms,
        "research_ms": research_ms,
        "analysis_ms": analysis_ms,
        "writer_ms": writer_ms,
        "total_ms": total,
    })
    _recompute(m)
    _save(m)


def update_corpus_stats(total_chunks: int, bills_ingested: int) -> None:
    """Call after ingestion or on app startup."""
    m = _load()
    m["total_chunks"] = total_chunks
    m["bills_ingested"] = bills_ingested
    _recompute(m)
    _save(m)


def get_all() -> dict[str, Any]:
    m = _load()
    _recompute(m)
    return m


def get_bullets() -> list[str]:
    """
    Returns a list of pre-formatted resume bullet strings.
    Only includes bullets where there's enough data to be credible (≥3 runs).
    """
    m = _load()
    bullets = []
    runs = m["total_queries"]

    if runs < 1:
        return ["Run the agent a few times to generate metrics."]

    if m["total_chunks"] > 0:
        bullets.append(
            f"Built agentic RAG pipeline over {m['total_chunks']:,}-chunk ChromaDB vector store "
            f"spanning {m['bills_ingested']} 118th Congress bills "
            f"(avg {m['avg_chunks_per_bill']} chunks/bill)"
        )

    total_ret = m["retrieval_strict_hits"] + m["retrieval_fallback_hits"]
    if total_ret >= 3:
        strict_pct = round(m["retrieval_strict_hits"] / total_ret * 100)
        bullets.append(
            f"Achieved {strict_pct}% strict metadata-filter retrieval hit rate "
            f"across {total_ret} ChromaDB queries, minimizing semantic fallback"
        )

    if m["json_parse_success_rate"] > 0 and runs >= 3:
        bullets.append(
            f"Maintained {m['json_parse_success_rate']}% structured JSON extraction rate "
            f"from LLM analysis node across {runs} agent runs "
            f"using schema-enforced prompting"
        )

    if m["web_search_calls"] >= 3:
        web_rate = round(m["web_search_successes"] /
                         m["web_search_calls"] * 100)
        bullets.append(
            f"Integrated Tavily web search with {web_rate}% success rate "
            f"across {m['web_search_calls']} calls for real-time legislative context"
        )

    if m["p95_total_ms"] > 0 and runs >= 3:
        bullets.append(
            f"End-to-end agent pipeline latency: "
            f"p50={m['p50_total_ms']:,}ms, p95={m['p95_total_ms']:,}ms "
            f"across {runs} queries "
            f"(Router {m['avg_router_ms']}ms · Research {m['avg_research_ms']}ms · "
            f"Analysis {m['avg_analysis_ms']}ms · Writer {m['avg_writer_ms']}ms)"
        )

    unique_count = len(set(m["unique_bills_analyzed"]))
    if unique_count >= 2:
        bullets.append(
            f"Analyzed {unique_count} unique bills across {runs} queries "
            f"with {m['avg_chunks_per_query']} avg chunks retrieved per run"
        )

    task_dist = m["task_distribution"]
    total_tasks = sum(task_dist.values())
    if total_tasks >= 3:
        top_task = max(task_dist, key=lambda k: task_dist[k])
        bullets.append(
            f"Multi-task routing: {task_dist['single']} impact analyses, "
            f"{task_dist['compare']} bill comparisons, "
            f"{task_dist['memo']} policy memos "
            f"— zero manual task selection"
        )

    return bullets
