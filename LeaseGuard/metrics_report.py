#!/usr/bin/env python3
"""
LeaseGuard Metrics CLI
=======================
    python metrics_report.py           # full report
    python metrics_report.py --bullets # resume bullets only
    python metrics_report.py --json    # raw JSON
"""

from src.metrics import get_all, get_resume_bullets
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

RESET = "\033[0m"
BOLD = "\033[1m"
AMBER = "\033[38;5;214m"
GREEN = "\033[38;5;107m"
MUTED = "\033[38;5;244m"
WHITE = "\033[97m"
RED = "\033[38;5;167m"


def bar(v, t, w=20, color=GREEN):
    f = int(round(v/t*w)) if t > 0 else 0
    return f"{color}{'█'*f}{MUTED}{'░'*(w-f)}{RESET}"


def pct_color(p):
    return GREEN if p >= 90 else AMBER if p >= 70 else RED


def section(t):
    print(f"\n{BOLD}{AMBER}{'─'*60}{RESET}")
    print(f"{BOLD}{WHITE}  {t}{RESET}")
    print(f"{BOLD}{AMBER}{'─'*60}{RESET}")


def row(label, value, note=""):
    n = f"  {MUTED}{note}{RESET}" if note else ""
    print(f"  {MUTED}{label:<32}{RESET}{BOLD}{WHITE}{value}{RESET}{n}")


def ms_fmt(v): return f"{v:,}ms" if v else "—"


def print_bullets(bullets):
    section("RESUME BULLET POINTS")
    print(f"  {MUTED}Copy these directly onto your resume.{RESET}\n")
    for b in bullets:
        print(f"  {AMBER}▸{RESET}  {WHITE}{b}{RESET}\n")


def print_full(m):
    runs = m["total_queries"]
    print(
        f"\n{BOLD}{AMBER}╔══════════════════════════════════════════════════════════╗")
    print(f"║          LeaseGuard  ·  Metrics Report                  ║")
    print(
        f"╚══════════════════════════════════════════════════════════╝{RESET}")
    if runs == 0:
        print(
            f"\n  {RED}No runs yet. Upload a lease and analyze it first.{RESET}\n")
        return

    section("CORPUS")
    row("Lease chunks (current session)", str(m["lease_chunks"]))
    row("State law chunks",               f"{m['law_chunks']:,}")
    row("States ingested",                str(m["states_ingested"]))

    section("RETRIEVAL QUALITY")
    total_ret = m["retrieval_strict_hits"] + m["retrieval_fallback_hits"]
    strict_pct = round(m["retrieval_strict_hits"] /
                       total_ret*100, 1) if total_ret > 0 else 0
    c = pct_color(strict_pct)
    row("Strict filter hit rate", f"{c}{strict_pct}%{RESET}", bar(
        strict_pct, 100, color=c))
    row("Fallback rate",          f"{round(100-strict_pct,1)}%")
    row("Avg chunks / query",     str(m["avg_chunks_per_query"]))
    jp = m["json_parse_success_rate"]
    jc = pct_color(jp)
    row("JSON parse success rate", f"{jc}{jp}%{RESET}", bar(jp, 100, color=jc))

    section("LATENCY")
    if m["p50_total_ms"]:
        row("p50 total", ms_fmt(m["p50_total_ms"]))
        row("p95 total", ms_fmt(m["p95_total_ms"]))
        print()
        row("  Avg Router",   ms_fmt(m["avg_router_ms"]))
        row("  Avg Research", ms_fmt(m["avg_research_ms"]))
        row("  Avg Analysis", ms_fmt(m["avg_analysis_ms"]))
        row("  Avg Writer",   ms_fmt(m["avg_writer_ms"]))
    else:
        print(f"  {MUTED}Run a few analyses to generate latency data.{RESET}")

    section("USAGE")
    row("Total analyses",       str(runs))
    row("Unique states",        str(len(set(m["unique_states"]))))
    row("Analyses today",       str(m["runs_today"]))
    td = m["task_distribution"]
    total_t = sum(td.values())
    print(f"\n  {MUTED}Task distribution:{RESET}")
    for task, label in [("flag_risks", "Flag risks"), ("explain_clause", "Explain clause"),
                        ("rights", "Know rights"), ("summary", "Summary"), ("compare", "Compare")]:
        count = td.get(task, 0)
        print(
            f"    {MUTED}{label:<20}{RESET}{AMBER}{count:>3}{RESET}  {bar(count,total_t,15)}")

    print_bullets(get_resume_bullets())
    print(f"  {MUTED}Stored at: data/metrics.json{RESET}\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--bullets", action="store_true")
    p.add_argument("--json",    action="store_true")
    args = p.parse_args()
    m = get_all()
    if args.json:
        print(json.dumps(m, indent=2))
    elif args.bullets:
        print_bullets(get_resume_bullets())
    else:
        print_full(m)


if __name__ == "__main__":
    main()
