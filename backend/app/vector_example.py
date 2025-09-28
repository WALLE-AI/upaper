"""Example demonstrating usage of vector and llm adapters."""
from __future__ import annotations
from app.vector.core import get_vector_store, VectorRecord
from app.llm.core import get_llm_provider

def example_flow():
    # Choose providers via args/env in real app
    vec = get_vector_store("chroma", persist_directory="./_chroma_db")
    llm = get_llm_provider("openai", api_key=None)  # set api_key in real usage
    texts = ["hello world", "foobar test"]

    # embeddings (may raise if provider not configured)
    embs = llm.embed(texts)
    records = [VectorRecord(id=f"doc:{i}", embedding=embs[i], metadata={"text": texts[i]}) for i in range(len(texts))]
    vec.upsert(records, namespace="demo")

    q_emb = llm.embed(["hello"])[0]
    hits = vec.query(q_emb, top_k=2, namespace="demo")
    print(hits)
