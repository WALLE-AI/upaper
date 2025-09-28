"""Domain dataclass for Paper entities (DB-agnostic)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(slots=True)
class Paper:
    id: str
    title: str
    month_url: str
    source_url: Optional[str] = None
    huggingface_url: Optional[str] = None
    date_str: Optional[str] = None
    paper_id: Optional[str] = None
    votes: Optional[int] = None
    ai_keywords: List[str] = field(default_factory=list)
    ai_summary: str = ""
    meta: Dict = field(default_factory=dict)
