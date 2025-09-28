"""SQLAlchemy-backed Paper repository returning dataclasses."""
from __future__ import annotations

import uuid
from typing import Iterable, Optional

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from ..models.paper import PaperModel
from ...domain.paper import Paper


def _to_dc(m: PaperModel) -> Paper:
    return Paper(
        id=m.id,
        title=m.title,
        month_url=m.month_url,
        source_url=m.source_url,
        huggingface_url=m.huggingface_url,
        date_str=m.date_str,
        paper_id=m.paper_id,
        votes=m.votes,
        ai_keywords=list(m.ai_keywords or []),
        ai_summary=m.ai_summary or "",
        meta=dict(m.meta or {}),
    )


class PaperRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, *, month_url: str | None = None, limit: int = 200) -> Iterable[Paper]:
        stmt: Select = select(PaperModel).order_by(PaperModel.created_at.desc()).limit(limit)
        if month_url:
            stmt = stmt.where(PaperModel.month_url == month_url)
        return [_to_dc(m) for m in self.session.scalars(stmt).all()]

    def get(self, paper_uuid: str) -> Optional[Paper]:
        m = self.session.get(PaperModel, paper_uuid)
        return _to_dc(m) if m else None

    def get_by_paper_id(self, paper_id: str) -> Optional[Paper]:
        stmt = select(PaperModel).where(PaperModel.paper_id == paper_id).limit(1)
        m = self.session.scalars(stmt).first()
        return _to_dc(m) if m else None


    def create(self, data: Paper) -> Paper:
        mid = data.id or str(uuid.uuid4())
        m = PaperModel(
            id=mid,
            title=data.title,
            month_url=data.month_url,
            source_url=data.source_url,
            huggingface_url=data.huggingface_url,
            date_str=data.date_str,
            paper_id=data.paper_id,
            votes=data.votes,
            ai_keywords=list(data.ai_keywords or []),
            ai_summary=data.ai_summary or "",
            meta=dict(data.meta or {}),
        )
        self.session.add(m)
        self.session.commit()
        self.session.refresh(m)
        return _to_dc(m)

    def update(self, paper_uuid: str, **fields) -> Optional[Paper]:
        m = self.session.get(PaperModel, paper_uuid)
        if not m:
            return None
        for k, v in fields.items():
            if hasattr(m, k):
                setattr(m, k, v)
        self.session.commit()
        self.session.refresh(m)
        return _to_dc(m)

    def delete(self, paper_uuid: str) -> bool:
        m = self.session.get(PaperModel, paper_uuid)
        if not m:
            return False
        self.session.delete(m)
        self.session.commit()
        return True
