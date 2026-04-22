from process_text import chunk_bill
from vector_db import get_vector_store
import json
import sys
import os
import time
import logging
from tqdm import tqdm
from google.api_core import exceptions

sys.path.append(os.path.dirname(__file__))

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')


def load_enriched_bills(file_path):
    db = get_vector_store()
    with open(file_path, "r") as f:
        bills = json.load(f)

    for bill in tqdm(bills, desc="Vectorizing Documents"):
        chunks = chunk_bill(bill)
        texts = [c['text'] for c in chunks]
        metadatas = [c['metadata'] for c in chunks]

        ids = [f"{bill['bill_number']}_{i}" for i in range(len(texts))]

        success = False
        while not success:
            try:
                db.add_texts(texts=texts, metadatas=metadatas, ids=ids)
                success = True
                time.sleep(1)  # Base throttle
            except Exception as e:
                if "429" in str(e):
                    logging.warning(f"Rate limit hit. Backing off 60s...")
                    time.sleep(60)
                else:
                    logging.error(f"Error loading {bill['bill_number']}: {e}")
                    break


if __name__ == "__main__":
    load_enriched_bills("data/enriched_bills.json")
