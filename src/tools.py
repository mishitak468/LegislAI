from __future__ import annotations

import os
import logging
from typing import Any

logger = logging.getLogger(__name__)


def retrieve_bill_chunks(bill_id: str, k: int = 6) -> list[str]:
    try:
        from src.vector_db import get_vector_store
        db = get_vector_store()

        results = db.similarity_search(
            f"legislative impact bill {bill_id}",
            k=k,
            filter={"bill_number": bill_id},
        )

        # Fallback
        if not results:
            try:
                results = db.similarity_search(
                    f"legislative impact bill {bill_id}",
                    k=k,
                    filter={"bill_number": int(bill_id)},
                )
            except Exception:
                pass

        # Final fallback
        if not results:
            results = db.similarity_search(
                f"bill number {bill_id} congress legislation", k=k
            )

        return [r.page_content for r in results]

    except Exception as e:
        logger.error(f"ChromaDB retrieval failed for bill {bill_id}: {e}")
        return []


def web_search_bill(bill_id: str, max_results: int = 4) -> list[str]:
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        logger.warning("TAVILY_API_KEY not set — skipping web search.")
        return [f"[Web search unavailable — set TAVILY_API_KEY for live news on bill {bill_id}]"]

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=tavily_key)
        response = client.search(
            query=f"US Congress H.R. {bill_id} 118th congress bill impact analysis",
            max_results=max_results,
            search_depth="advanced",
        )
        snippets = []
        for r in response.get("results", []):
            title = r.get("title", "")
            content = r.get("content", "")
            url = r.get("url", "")
            snippets.append(f"[{title}] {content[:400]}  (source: {url})")
        return snippets

    except Exception as e:
        logger.error(f"Web search failed for bill {bill_id}: {e}")
        return [f"[Web search error for bill {bill_id}: {str(e)[:80]}]"]


def compare_bills_tool(
    risk_scores: dict[str, dict[str, float]],
    sectors: dict[str, list[str]],
) -> dict[str, Any]:
    if len(risk_scores) < 2:
        return {}

    all_sectors: set[str] = set()
    for s_list in sectors.values():
        all_sectors.update(s_list)

    head_to_head: dict[str, dict[str, float]] = {}
    for sector in sorted(all_sectors):
        head_to_head[sector] = {
            bill_id: scores.get(sector, 0)
            for bill_id, scores in risk_scores.items()
        }

    averages = {
        bill_id: sum(scores.values()) / max(len(scores), 1)
        for bill_id, scores in risk_scores.items()
    }
    winner = min(averages, key=lambda b: averages[b])

    return {
        "head_to_head": head_to_head,
        "average_risk": averages,
        "lowest_risk_bill": winner,
    }
