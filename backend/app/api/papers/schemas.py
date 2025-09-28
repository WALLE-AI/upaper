"""Pydantic request/response schemas for Papers API."""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PaperCreateIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    month_url: str = Field(..., min_length=1, max_length=300)
    source_url: Optional[str] = None
    huggingface_url: Optional[str] = None
    date_str: Optional[str] = None
    paper_id: Optional[str] = None
    votes: Optional[int] = None
    ai_keywords: List[str] = Field(default_factory=list)
    ai_summary: str = ""
    meta: Dict[str, Any] = Field(default_factory=dict)


class PaperUpdateIn(BaseModel):
    title: Optional[str] = Field(default=None, max_length=500)
    month_url: Optional[str] = Field(default=None, max_length=300)
    source_url: Optional[str] = None
    huggingface_url: Optional[str] = None
    date_str: Optional[str] = None
    paper_id: Optional[str] = None
    votes: Optional[int] = None
    ai_keywords: Optional[List[str]] = None
    ai_summary: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class PaperOut(BaseModel):
    id: str
    title: str
    month_url: str
    source_url: Optional[str]
    huggingface_url: Optional[str]
    date_str: Optional[str]
    paper_id: Optional[str]
    votes: Optional[int]
    ai_keywords: List[str]
    ai_summary: str
    meta: Dict[str, Any]
