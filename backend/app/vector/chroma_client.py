"""Chroma VectorStore implementation (requires chromadb)."""
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import chromadb
    from chromadb.config import Settings
except Exception:
    chromadb = None
    Settings = None

from .core import VectorStore, VectorRecord

class ChromaVectorStore(VectorStore):
    def __init__(self, persist_directory: Optional[str] = None, chroma_server: Optional[str] = None, **_):
        if chromadb is None:
            raise RuntimeError("chromadb is not available")
        if chroma_server:
            self.client = chromadb.HttpClient(url=chroma_server)
        else:
            settings = Settings(chroma_db_impl="duckdb+parquet", persist_directory=persist_directory)
            self.client = chromadb.Client(settings=settings)
        self.collection_cache = {}

    def _get_collection(self, namespace: Optional[str]):
        name = f"chroma_{namespace or 'default'}"
        if name not in self.collection_cache:
            self.collection_cache[name] = self.client.get_or_create_collection(name=name)
        return self.collection_cache[name]

    def create_collection(self, name: str, dims: int, namespace: Optional[str] = None) -> None:
        self._get_collection(namespace or name)

    def upsert(self, records: Iterable[VectorRecord], namespace: Optional[str] = None) -> None:
        coll = self._get_collection(namespace)
        ids = [r["id"] for r in records]
        embeddings = [r["embedding"] for r in records]
        metadatas = [r.get("metadata", {}) for r in records]
        documents = [r.get("metadata", {}).get("document", "") for r in records]
        coll.upsert(ids=ids, embeddings=embeddings, metadatas=metadatas, documents=documents)

    def query(self, embedding: List[float], top_k: int = 10, namespace: Optional[str] = None
             ) -> List[Tuple[str, float, Dict[str, Any]]]:
        coll = self._get_collection(namespace)
        res = coll.query(query_embeddings=[embedding], n_results=top_k, include=["metadatas", "distances", "ids"])
        rows = res["ids"][0]
        dists = res["distances"][0]
        metas = res["metadatas"][0]
        return [(rid, float(score), meta or {}) for rid, score, meta in zip(rows, dists, metas)]

    def delete(self, ids: Iterable[str], namespace: Optional[str] = None) -> None:
        coll = self._get_collection(namespace)
        coll.delete(ids=list(ids))
