"""Supabase-backed Paper repository using supabase-py v2."""
from __future__ import annotations

import uuid
from typing import Any, Dict, Iterable, Optional

from supabase import Client

from ...domain.paper import Paper


def _row_to_dc(row: Dict[str, Any]) -> Paper:
    return Paper(
        id=str(row.get("id")),
        title=row.get("title", ""),
        month_url=row.get("month_url", ""),
        source_url=row.get("source_url"),
        huggingface_url=row.get("huggingface_url"),
        date_str=row.get("date_str"),
        paper_id=row.get("paper_id"),
        votes=row.get("votes"),
        ai_keywords=list(row.get("ai_keywords") or []),
        ai_summary=row.get("ai_summary") or "",
        meta=dict(row.get("meta") or {}),
    )


class PaperRepositorySupabase:
    def __init__(self, client: Client) -> None:
        self.client = client
        self.table = client.table("daily_papers")

    def list(self, *, month_url: str | None = None, limit: int = 200) -> Iterable[Paper]:
        q = self.table.select("*").order("created_at", desc=True).limit(limit)
        if month_url:
            q = q.eq("month_url", month_url)
        res = q.execute()
        rows = res.data or []
        return [_row_to_dc(r) for r in rows]

    def get(self, paper_uuid: str) -> Optional[Paper]:
        res = self.table.select("*").eq("id", paper_uuid).limit(1).execute()
        rows = res.data or []
        return _row_to_dc(rows[0]) if rows else None

    def get_by_paper_id(self, paper_id: str) -> Optional[Paper]:
        res = self.table.select("*").eq("paper_id", paper_id).limit(1).execute()
        rows = res.data or []
        return _row_to_dc(rows[0]) if rows else None
    
    
    def get_by_paper_month(self, month: str) -> Optional[Paper]:
        year, month = month.split('-')
        res = self.table.select("*").filter('date', 'gte', f'{year}-{month}-01').filter('date', 'lt', f'{year}-{int(month)+1:02d}-01').execute()
        rows = res.data or []
        return [_row_to_dc(row) for row in rows] if rows else None

    def create(self, data: Paper) -> Paper:
        row = {
            "id": data.id or str(uuid.uuid4()),
            "title": data.title,
            "month_url": data.month_url,
            "source_url": data.source_url,
            "huggingface_url": data.huggingface_url,
            "date": data.date_str,
            "paper_id": data.paper_id,
            "votes": data.votes,
            "ai_keywords": data.ai_keywords or [],
            "ai_summary": data.ai_summary or "",
            "meta": data.meta or {},
        }
        res = self.table.insert(row).execute()
        created = (res.data or [])[0]
        return _row_to_dc(created)

    def update(self, paper_uuid: str, **fields) -> Optional[Paper]:
        allowed = {
            "title", "month_url", "source_url", "huggingface_url", "date",
            "paper_id", "votes", "ai_keywords", "ai_summary", "meta"
        }
        body = {k: v for k, v in fields.items() if k in allowed}
        if not body:
            return self.get(paper_uuid)
        res = self.table.update(body).eq("id", paper_uuid).execute()
        rows = res.data or []
        return _row_to_dc(rows[0]) if rows else None

    def delete(self, paper_uuid: str) -> bool:
        self.table.delete().eq("id", paper_uuid).execute()
        return True
