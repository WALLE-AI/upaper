"""Milvus VectorStore implementation (requires pymilvus)."""
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility
except Exception:  # pragma: no cover - allow package absence in test env
    connections = None
    FieldSchema = CollectionSchema = DataType = Collection = utility = None

from .core import VectorStore, VectorRecord

class MilvusVectorStore(VectorStore):
    def __init__(self, alias: str = "default", host: Optional[str] = None, port: Optional[int] = None, **_):
        if connections is None:
            raise RuntimeError("pymilvus is not available")
        if host and port:
            connections.connect(alias=alias, host=host, port=port)
        else:
            connections.connect(alias=alias)
        self.alias = alias

    def _collection_name(self, namespace: Optional[str]) -> str:
        return f"collection_{namespace or 'default'}"

    def create_collection(self, name: str, dims: int, namespace: Optional[str] = None) -> None:
        coll_name = self._collection_name(namespace or name)
        if utility.has_collection(coll_name, using=self.alias):
            return
        fields = [
            FieldSchema(name="id", dtype=DataType.VARCHAR, is_primary=True, max_length=64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dims),
            FieldSchema(name="metadata", dtype=DataType.JSON)
        ]
        schema = CollectionSchema(fields, description="app vectors")
        Collection(coll_name, schema=schema, using=self.alias)

    def upsert(self, records: Iterable[VectorRecord], namespace: Optional[str] = None) -> None:
        coll_name = self._collection_name(namespace)
        coll = Collection(coll_name, using=self.alias)
        ids = [r["id"] for r in records]
        embeddings = [r["embedding"] for r in records]
        metas = [r.get("metadata", {}) for r in records]
        coll.insert([ids, embeddings, metas])
        coll.flush()

    def query(self, embedding: List[float], top_k: int = 10, namespace: Optional[str] = None
             ) -> List[Tuple[str, float, Dict[str, Any]]]:
        coll_name = self._collection_name(namespace)
        coll = Collection(coll_name, using=self.alias)
        res = coll.search([embedding], "embedding", params={"metric_type": "IP", "params": {"nprobe": 10}}, limit=top_k, output_fields=["id", "metadata"])
        out = []
        for hits in res:
            for h in hits:
                meta = h.entity.get("metadata") if hasattr(h, "entity") else {}
                out.append((h.id, float(h.score), meta or {}))
        return out

    def delete(self, ids: Iterable[str], namespace: Optional[str] = None) -> None:
        coll_name = self._collection_name(namespace)
        coll = Collection(coll_name, using=self.alias)
        coll.delete(f"id in {list(ids)}")
        coll.flush()
