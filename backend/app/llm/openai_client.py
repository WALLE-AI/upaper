"""OpenAI wrapper exposing embed() and chat_completion() like openai-python."""
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional

try:
    import openai
except Exception:
    openai = None

from .core import EmbeddingProvider, CompletionProvider

class OpenAIProvider(EmbeddingProvider, CompletionProvider):
    def __init__(self, api_key: Optional[str] = None, organization: Optional[str] = None):
        if openai is None:
            raise RuntimeError("openai package not available")
        if api_key:
            openai.api_key = api_key
        if organization:
            openai.organization = organization

    def embed(self, texts: Iterable[str], model: str = "text-embedding-3-small") -> List[List[float]]:
        resp = openai.Embedding.create(model=model, input=list(texts))
        return [item["embedding"] for item in resp["data"]]

    def chat_completion(self, messages: Iterable[Dict[str,str]], model: str = "gpt-4o-mini", temperature: float = 0.0, max_tokens: Optional[int] = None) -> Dict[str, Any]:
        resp = openai.ChatCompletion.create(model=model, messages=list(messages), temperature=temperature, max_tokens=max_tokens)
        return resp
