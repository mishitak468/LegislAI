from src.metrics import get_all, get_bullets
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
BLUE = "\033[38;5;110m"


def bar(value, total, width=20, color=GREEN):
    filled = int(round(value / total * width)) if total > 0 else 0
    return f"{color}{'█' * filled}{MUTED}{'░' * (width - filled)}{RESET}"


def pct_color(p):
    if p >= 90:
        return GREEN
    if p >= 70:
        return AMBER
    return RED


def section(title):
    print(f"\n{BOLD}{AMBER}{'─' * 60}{RESET}")
    print(f"{BOLD}{WHITE}  {title}{RESET}")
    print(f"{BOLD}{AMBER}{'─' * 60}{RESET}")


def row(label, value, note=""):
    note_str = f"  {MUTED}{note}{RESET}" if note else ""
    print(f"  {MUTED}{label:<32}{RESET}{BOLD}{WHITE}{value}{RESET}{note_str}")


def ms_fmt(v):
    return f"{v:,}ms" if v else "—"


def print_bullets(bullets):
    section("BULLET POINTS")
    print(f"  {MUTED}Copy these.{RESET}\n")
    for b in bullets:
        print(f"  {AMBER}▸{RESET}  {WHITE}{b}{RESET}\n")


def print_full_report(m):
    runs = m["total_queries"]

    print(
        f"\n{BOLD}{AMBER}╔══════════════════════════════════════════════════════════╗")
    print(f"║            LegislAI  ·  Metrics Report                  ║")
    print(
        f"╚══════════════════════════════════════════════════════════╝{RESET}")

    if runs == 0:
        print(
            f"\n  {RED}No runs recorded yet. Run the Streamlit app and execute a query first.{RESET}\n")
        return

    section("CORPUS COVERAGE")
    row("Vector store chunks",   f"{m['total_chunks']:,}")
    row("Bills ingested",        str(m['bills_ingested']))
    row("Avg chunks / bill",     str(m['avg_chunks_per_bill']))
    cov = round(m['bills_ingested'] / 17000 * 100,
                2) if m['bills_ingested'] > 0 else 0
    row("118th Congress coverage", f"{cov}%", "(~17,000 bills introduced)")

    section("RETRIEVAL QUALITY  (AI/ML)")
    total_ret = m["retrieval_strict_hits"] + m["retrieval_fallback_hits"]
    strict_pct = round(m["retrieval_strict_hits"] /
                       total_ret * 100, 1) if total_ret > 0 else 0
    color = pct_color(strict_pct)
    row("Total retrieval calls",  str(total_ret))
    row("Strict filter hit rate", f"{color}{strict_pct}%{RESET}",
        f"{bar(strict_pct, 100, color=color)}")
    row("Semantic fallback rate", f"{round(100-strict_pct,1)}%")
    row("Avg chunks / query",     str(m['avg_chunks_per_query']))

    jp = m['json_parse_success_rate']
    jcolor = pct_color(jp)
    row("JSON parse success rate", f"{jcolor}{jp}%{RESET}",
        f"{bar(jp, 100, color=jcolor)}")
    row("Parse successes",  str(m['analysis_json_successes']))
    row("Parse failures",   str(m['analysis_json_failures']))

    if m["web_search_calls"] > 0:
        section("WEB SEARCH  (Tavily)")
        ws_rate = round(m["web_search_successes"] /
                        m["web_search_calls"] * 100, 1)
        wcolor = pct_color(ws_rate)
        row("Total web search calls",    str(m["web_search_calls"]))
        row("Web search success rate",   f"{wcolor}{ws_rate}%{RESET}",
            f"{bar(ws_rate, 100, color=wcolor)}")
        row("Successful searches",       str(m["web_search_successes"]))
        row("Failed / unavailable",      str(m["web_search_failures"]))

    section("PIPELINE LATENCY  (Systems Design)")
    if m['p50_total_ms']:
        row("p50 end-to-end",   ms_fmt(m['p50_total_ms']))
        row("p95 end-to-end",   ms_fmt(m['p95_total_ms']))
        print()
        row("  Avg Router node",   ms_fmt(m['avg_router_ms']))
        row("  Avg Research node", ms_fmt(m['avg_research_ms']))
        row("  Avg Analysis node", ms_fmt(m['avg_analysis_ms']))
        row("  Avg Writer node",   ms_fmt(m['avg_writer_ms']))

        records = m.get("latency_records", [])
        if len(records) >= 2:
            print(f"\n  {MUTED}Last {min(10, len(records))} run totals:{RESET}")
            for r in records[-10:]:
                print(
                    f"    {MUTED}{r['ts'][:16]}{RESET}  {AMBER}{r['total_ms']:>6,}ms{RESET}")
    else:
        print(f"  {MUTED}Run the agent a few times to generate latency data.{RESET}")

    section("USAGE & SCALE")
    row("Total queries",         str(runs))
    row("Unique bills analyzed", str(len(set(m["unique_bills_analyzed"]))))
    row("Queries today",         str(m["runs_today"]))
    row("First run",             (m["first_run"] or "—")[:16])
    row("Last run",              (m["last_run"] or "—")[:16])

    td = m["task_distribution"]
    print(f"\n  {MUTED}Task distribution:{RESET}")
    total_tasks = sum(td.values())
    for task, label in [("single", "Single analysis"), ("compare", "Comparison"), ("memo", "Policy memo")]:
        count = td[task]
        pct = round(count / total_tasks * 100) if total_tasks > 0 else 0
        print(
            f"    {MUTED}{label:<20}{RESET}{AMBER}{count:>3}{RESET}  {bar(count, total_tasks, width=15)}")

    bullets = get_bullets()
    print_bullets(bullets)

    print(f"  {MUTED}Metrics stored at: data/metrics.json{RESET}\n")


def main():
    parser = argparse.ArgumentParser(
        description="LegislAI metrics CLI — prints stats and bullets from data/metrics.json"
    )
    parser.add_argument("--bullets", action="store_true",
                        help="Print bullets only")
    parser.add_argument("--json",    action="store_true",
                        help="Dump raw metrics JSON")
    args = parser.parse_args()

    m = get_all()

    if args.json:
        print(json.dumps(m, indent=2))
        return

    if args.bullets:
        bullets = get_bullets()
        print_bullets(bullets)
        return

    print_full_report(m)


if __name__ == "__main__":
    main()
