"""Abstract LLM provider interfaces and factory."""
from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Protocol

class EmbeddingProvider(Protocol):
    def embed(self, texts: Iterable[str], model: Optional[str] = None) -> List[List[float]]: ...

class CompletionProvider(Protocol):
    def chat_completion(self, messages: Iterable[Dict[str,str]], model: Optional[str] = None,
                        temperature: float = 0.0, max_tokens: Optional[int] = None) -> Dict[str, Any]: ...

def get_llm_provider(kind: str, **kwargs):
    kind = kind.lower()
    if kind == "openai":
        from .openai_client import OpenAIProvider
        return OpenAIProvider(**kwargs)
    if kind == "openrouter":
        from .openrouter_client import OpenRouterProvider
        return OpenRouterProvider(**kwargs)
    raise ValueError(f"unsupported llm provider: {kind}")
