"""
LeaseGuard — Lease PDF Processor
=================================
Handles PDF text extraction and chunking for user-uploaded leases.
Uses pdfplumber for clean text extraction (handles multi-column layouts).
Falls back to pypdf if pdfplumber is not installed.
"""

from __future__ import annotations

import re
from typing import IO


# ── PDF Text Extraction ───────────────────────────────────────────────────────

def extract_text_from_pdf(file: IO[bytes]) -> str:
    """
    Extract raw text from a PDF file object.
    Tries pdfplumber first (better layout handling), falls back to pypdf.
    """
    try:
        import pdfplumber
        with pdfplumber.open(file) as pdf:
            pages = []
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    pages.append(text)
        return "\n\n".join(pages)
    except ImportError:
        pass

    try:
        from pypdf import PdfReader
        reader = PdfReader(file)
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
    except Exception as e:
        raise RuntimeError(f"Could not extract PDF text: {e}")


# ── Text Cleaning ─────────────────────────────────────────────────────────────

def clean_lease_text(raw: str) -> str:
    """
    Clean extracted lease text:
    - Remove excessive whitespace and blank lines
    - Normalize section numbers
    - Strip page headers/footers (common patterns)
    """
    # Remove repeated whitespace
    text = re.sub(r"[ \t]{2,}", " ", raw)
    # Collapse 3+ newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove common page footer patterns like "Page 1 of 12"
    text = re.sub(r"Page\s+\d+\s+of\s+\d+", "", text, flags=re.IGNORECASE)
    # Remove lines that are just numbers (page numbers)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.MULTILINE)
    return text.strip()


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_lease(text: str, chunk_size: int = 800, overlap: int = 150) -> list[dict]:
    """
    Split lease text into overlapping chunks with metadata.
    Tries to split on section boundaries first, then falls back to fixed size.

    Returns list of { text, metadata: { source, chunk_index, char_start } }
    """
    # Try splitting on section headers first (e.g. "1.", "SECTION 2", "Article III")
    section_pattern = re.compile(
        r"(?=\n(?:\d+\.|SECTION\s+\d+|Article\s+[IVXLC]+|[A-Z]{2,}\.)\s)",
        re.IGNORECASE,
    )
    sections = section_pattern.split(text)

    chunks = []
    chunk_index = 0
    char_cursor = 0

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # If section fits in one chunk, keep it whole
        if len(section) <= chunk_size:
            chunks.append({
                "text": section,
                "metadata": {
                    "source": "lease",
                    "chunk_index": chunk_index,
                    "char_start": char_cursor,
                }
            })
            chunk_index += 1
            char_cursor += len(section)
        else:
            # Slide through oversized sections
            start = 0
            while start < len(section):
                end = start + chunk_size
                chunk_text = section[start:end].strip()
                if chunk_text:
                    chunks.append({
                        "text": chunk_text,
                        "metadata": {
                            "source": "lease",
                            "chunk_index": chunk_index,
                            "char_start": char_cursor + start,
                        }
                    })
                    chunk_index += 1
                start += chunk_size - overlap

            char_cursor += len(section)

    return chunks


# ── Main Entry Point ──────────────────────────────────────────────────────────

def process_lease_pdf(file: IO[bytes]) -> list[dict]:
    """
    Full pipeline: extract → clean → chunk.
    Returns list of chunk dicts ready for ChromaDB ingestion.
    """
    raw   = extract_text_from_pdf(file)
    clean = clean_lease_text(raw)
    return chunk_lease(clean)