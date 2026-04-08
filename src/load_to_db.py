from process_text import chunk_bill
from vector_db import get_vector_store
import json
import sys
import os

sys.path.append(os.path.dirname(__file__))


def load_enriched_bills(file_path):
    """Main pipeline to move data from JSON to ChromaDB."""

    print("Connecting to Vector DB...")
    db = get_vector_store()

    with open(file_path, "r") as f:
        bills = json.load(f)

    total_chunks = 0

    for bill in bills:
        print(f"Chunking and Embedding: {bill['bill_number']}...")

        chunks_with_metadata = chunk_bill(bill)

        texts = [c['text'] for c in chunks_with_metadata]
        metadatas = [c['metadata'] for c in chunks_with_metadata]

        db.add_texts(texts=texts, metadatas=metadatas)

        total_chunks += len(texts)
        print(f"Added {len(texts)} chunks for {bill['bill_number']}")

    print(f"\nSuccess! Total chunks in DB: {total_chunks}")


if __name__ == "__main__":
    load_enriched_bills("data/enriched_bills.json")
