"""Paper ORM model compatible with PostgreSQL(Supabase) and MySQL."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from ..base import Base


class PaperModel(Base):
    __tablename__ = "daily_papers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID string
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(1000), default=None)
    huggingface_url: Mapped[Optional[str]] = mapped_column(String(1000), default=None)
    date_str: Mapped[Optional[str]] = mapped_column(String(40), default=None)
    paper_id: Mapped[Optional[str]] = mapped_column(String(200), default=None, index=True)
    votes: Mapped[Optional[int]] = mapped_column(Integer, default=None)

    ai_keywords: Mapped[List[str]] = mapped_column(JSON, default=list)
    ai_summary: Mapped[str] = mapped_column(Text, default="")
    month_url: Mapped[str] = mapped_column(String(300), nullable=False)

    meta: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now(), nullable=False)
