"""
LeaseGuard — State Tenant Law Ingestion
========================================
Downloads tenant law summaries for all 50 US states and ingests
them into the state_tenant_laws ChromaDB collection.

Data source: Nolo.com state-by-state tenant rights pages (publicly available)
and state attorney general tenant rights PDFs.

Run once before launching the app:
    python src/ingest_state_laws.py

Or for a specific state:
    python src/ingest_state_laws.py --state NY
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from dotenv import load_dotenv
from tqdm import tqdm

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ── State law source URLs ──────────────────────────────────────────────────────
# Each maps to a publicly available tenant rights page or PDF.
# These are plain-text summaries of state landlord-tenant law.
STATE_LAW_URLS: dict[str, str] = {
    "AL": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-alabama.html",
    "AK": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-alaska.html",
    "AZ": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-arizona.html",
    "AR": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-arkansas.html",
    "CA": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-california.html",
    "CO": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-colorado.html",
    "CT": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-connecticut.html",
    "DE": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-delaware.html",
    "FL": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-florida.html",
    "GA": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-georgia.html",
    "HI": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-hawaii.html",
    "ID": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-idaho.html",
    "IL": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-illinois.html",
    "IN": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-indiana.html",
    "IA": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-iowa.html",
    "KS": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-kansas.html",
    "KY": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-kentucky.html",
    "LA": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-louisiana.html",
    "ME": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-maine.html",
    "MD": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-maryland.html",
    "MA": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-massachusetts.html",
    "MI": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-michigan.html",
    "MN": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-minnesota.html",
    "MS": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-mississippi.html",
    "MO": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-missouri.html",
    "MT": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-montana.html",
    "NE": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-nebraska.html",
    "NV": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-nevada.html",
    "NH": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-new-hampshire.html",
    "NJ": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-new-jersey.html",
    "NM": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-new-mexico.html",
    "NY": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-new-york.html",
    "NC": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-north-carolina.html",
    "ND": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-north-dakota.html",
    "OH": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-ohio.html",
    "OK": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-oklahoma.html",
    "OR": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-oregon.html",
    "PA": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-pennsylvania.html",
    "RI": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-rhode-island.html",
    "SC": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-south-carolina.html",
    "SD": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-south-dakota.html",
    "TN": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-tennessee.html",
    "TX": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-texas.html",
    "UT": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-utah.html",
    "VT": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-vermont.html",
    "VA": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-virginia.html",
    "WA": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-washington.html",
    "WV": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-west-virginia.html",
    "WI": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-wisconsin.html",
    "WY": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-wyoming.html",
    "DC": "https://www.nolo.com/legal-encyclopedia/overview-landlord-tenant-laws-district-columbia.html",
}


def fetch_state_law_text(state_code: str, url: str) -> str | None:
    """Fetch and extract plain text from a state law page."""
    try:
        import requests
        from bs4 import BeautifulSoup

        headers = {
            "User-Agent": "Mozilla/5.0 LeaseGuard/1.0 (educational tool)"}
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"{state_code}: HTTP {resp.status_code}")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")

        # Remove nav, footer, ads
        for tag in soup(["nav", "footer", "header", "script", "style", "aside"]):
            tag.decompose()

        # Get main content
        main = soup.find("main") or soup.find("article") or soup.find("body")
        text = main.get_text(separator="\n", strip=True) if main else ""

        # Prepend state identifier so retrieval can filter
        return f"STATE: {state_code}\n\n{text}"

    except Exception as e:
        logger.error(f"{state_code}: fetch failed — {e}")
        return None


def chunk_law_text(text: str, state_code: str, chunk_size: int = 600) -> list[dict]:
    """Chunk state law text into overlapping segments with state metadata."""
    import re
    paragraphs = re.split(r"\n{2,}", text)
    chunks = []
    current = ""
    idx = 0

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current) + len(para) < chunk_size:
            current += "\n\n" + para
        else:
            if current.strip():
                chunks.append({
                    "text": current.strip(),
                    "metadata": {"state": state_code, "source": "tenant_law", "chunk_index": idx}
                })
                idx += 1
            current = para

    if current.strip():
        chunks.append({
            "text": current.strip(),
            "metadata": {"state": state_code, "source": "tenant_law", "chunk_index": idx}
        })

    return chunks


def ingest_state(state_code: str) -> int:
    """Fetch, chunk, and ingest one state. Returns number of chunks added."""
    from src.vector_db import get_law_store
    url = STATE_LAW_URLS.get(state_code.upper())
    if not url:
        logger.error(f"No URL for state: {state_code}")
        return 0

    text = fetch_state_law_text(state_code, url)
    if not text:
        return 0

    chunks = chunk_law_text(text, state_code)
    if not chunks:
        return 0

    db = get_law_store()
    texts = [c["text"] for c in chunks]
    metas = [c["metadata"] for c in chunks]
    ids = [f"{state_code}_{i}" for i in range(len(chunks))]

    try:
        db.add_texts(texts=texts, metadatas=metas, ids=ids)
        return len(chunks)
    except Exception as e:
        logger.error(f"{state_code}: ingest failed — {e}")
        return 0


def main():
    parser = argparse.ArgumentParser(
        description="Ingest state tenant laws into ChromaDB")
    parser.add_argument("--state", help="Ingest one state only (e.g. NY)")
    args = parser.parse_args()

    if args.state:
        states = [args.state.upper()]
    else:
        states = list(STATE_LAW_URLS.keys())

    total_chunks = 0
    for state_code in tqdm(states, desc="Ingesting state laws"):
        n = ingest_state(state_code)
        total_chunks += n
        logger.info(f"{state_code}: {n} chunks ingested")
        time.sleep(1.5)  # polite rate limit

    print(
        f"\n✅ Done. {total_chunks} total chunks across {len(states)} states.")


if __name__ == "__main__":
    main()
