"""
LeaseGuard Tools
================
Three retrieval tools used by the Research node:
  1. retrieve_lease_chunks  — from the user's uploaded lease (session collection)
  2. retrieve_law_chunks    — from pre-ingested state tenant law corpus
  3. web_search_tenant_law  — live Tavily search
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

LEASE_COLLECTION  = "lease_session"     # cleared & reloaded on each upload
LAW_COLLECTION    = "state_tenant_laws" # pre-ingested, persistent


# ── Tool 1: Lease retrieval ───────────────────────────────────────────────────

def retrieve_lease_chunks(query: str, k: int = 6) -> list[str]:
    """Retrieve top-k chunks from the currently uploaded lease."""
    try:
        from src.vector_db import get_lease_store
        db = get_lease_store()
        results = db.similarity_search(query, k=k)
        return [r.page_content for r in results]
    except Exception as e:
        logger.error(f"Lease retrieval failed: {e}")
        return []


# ── Tool 2: State law retrieval ───────────────────────────────────────────────

def retrieve_law_chunks(query: str, state_code: str, k: int = 4) -> list[str]:
    """
    Retrieve top-k tenant law chunks for the given state.
    Uses a metadata filter on state_code if provided.
    """
    try:
        from src.vector_db import get_law_store
        db = get_law_store()

        if state_code:
            results = db.similarity_search(
                query, k=k, filter={"state": state_code}
            )
            if not results:
                # Fallback: no filter, just semantic search
                results = db.similarity_search(query, k=k)
        else:
            results = db.similarity_search(query, k=k)

        return [r.page_content for r in results]
    except Exception as e:
        logger.error(f"Law retrieval failed: {e}")
        return []


# ── Tool 3: Web search ────────────────────────────────────────────────────────

def web_search_tenant_law(query: str, max_results: int = 3) -> list[str]:
    """Search Tavily for current tenant rights info."""
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        return ["[Web search unavailable — set TAVILY_API_KEY for live tenant law results]"]
    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=tavily_key)
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
        )
        snippets = []
        for r in response.get("results", []):
            title   = r.get("title", "")
            content = r.get("content", "")
            url     = r.get("url", "")
            snippets.append(f"[{title}] {content[:400]}  (source: {url})")
        return snippets
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return [f"[Web search error: {str(e)[:80]}]"]