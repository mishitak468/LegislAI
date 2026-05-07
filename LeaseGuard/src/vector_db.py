from __future__ import annotations
import os
from functools import lru_cache
from typing import List
import chromadb
import requests
from langchain_chroma import Chroma
from langchain_core.embeddings import Embeddings

CHROMA_PATH      = "data/chroma_db"
LEASE_COLLECTION = "lease_session"
LAW_COLLECTION   = "state_tenant_laws"

class GeminiEmbeddings(Embeddings):
    def __init__(self, model: str = "gemini-embedding-001"):
        self.model = model
        self.api_key = os.environ["GOOGLE_API_KEY"]
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent"
    def _embed(self, text: str) -> List[float]:
        response = requests.post(self.url, params={"key": self.api_key},
            json={"model": f"models/{self.model}", "content": {"parts": [{"text": text}]}}, timeout=30)
        response.raise_for_status()
        return response.json()["embedding"]["values"]
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(t) for t in texts]
    def embed_query(self, text: str) -> List[float]:
        return self._embed(text)

def _embeddings() -> GeminiEmbeddings:
    return GeminiEmbeddings()

def get_lease_store() -> Chroma:
    return Chroma(collection_name=LEASE_COLLECTION, embedding_function=_embeddings(), persist_directory=CHROMA_PATH)

@lru_cache(maxsize=1)
def get_law_store() -> Chroma:
    return Chroma(collection_name=LAW_COLLECTION, embedding_function=_embeddings(), persist_directory=CHROMA_PATH)

def clear_lease_store() -> None:
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    try: client.delete_collection(LEASE_COLLECTION)
    except Exception: pass

def lease_chunk_count() -> int:
    try: return get_lease_store()._collection.count()
    except Exception: return 0

def law_chunk_count() -> int:
    try: return get_law_store()._collection.count()
    except Exception: return 0
