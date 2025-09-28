"""OpenRouter HTTP adapter (example)."""
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional
import httpx

from .core import EmbeddingProvider, CompletionProvider

class OpenRouterProvider(EmbeddingProvider, CompletionProvider):
    def __init__(self, api_key: str, base_url: str = "https://api.openrouter.ai/v1"):
        self.client = httpx.Client(timeout=30.0)
        self.api_key = api_key
        self.base = base_url

    def embed(self, texts: Iterable[str], model: str = "text-embedding-3-small") -> List[List[float]]:
        url = f"{self.base}/embeddings"
        payload = {"model": model, "input": list(texts)}
        headers = {"Authorization": f"Bearer {self.api_key}"}
        r = self.client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        j = r.json()
        return [d["embedding"] for d in j.get("data", [])]

    def chat_completion(self, messages: Iterable[Dict[str,str]], model: str = "gpt-4o-mini", temperature: float = 0.0, max_tokens: Optional[int] = None):
        url = f"{self.base}/chat/completions"
        payload = {"model": model, "messages": list(messages), "temperature": temperature}
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        headers = {"Authorization": f"Bearer {self.api_key}"}
        r = self.client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        return r.json()
