"""Abstract VectorStore interface and factory."""
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Protocol, Tuple

class VectorRecord(dict):
    """Simple dict-based record: keys: id, embedding, metadata"""
    pass

class VectorStore(Protocol):
    def upsert(self, records: Iterable[VectorRecord], namespace: Optional[str] = None) -> None: ...
    def query(self, embedding: List[float], top_k: int = 10, namespace: Optional[str] = None
             ) -> List[Tuple[str, float, Dict[str, Any]]]: ...
    def delete(self, ids: Iterable[str], namespace: Optional[str] = None) -> None: ...
    def create_collection(self, name: str, dims: int, namespace: Optional[str] = None) -> None: ...

def get_vector_store(kind: str, **kwargs) -> VectorStore:
    kind = kind.lower()
    if kind == "milvus":
        from .milvus_client import MilvusVectorStore
        return MilvusVectorStore(**kwargs)
    if kind == "chroma":
        from .chroma_client import ChromaVectorStore
        return ChromaVectorStore(**kwargs)
    raise ValueError(f"unsupported vector store: {kind}")
