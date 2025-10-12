"""Paper service encapsulating business rules."""
from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy.orm import Session

from ..domain.paper import Paper
from ..db.repositories.factory import paper_repo


class PaperService:
    def __init__(self, session: Session) -> None:
        self.repo = paper_repo(session)

    def list_papers(self, month_url: str | None = None, limit: int = 200) -> Iterable[Paper]:
        return self.repo.list(month_url=month_url, limit=limit)

    def create_paper(self, data: Paper) -> Paper:
        return self.repo.create(data)

    def get_paper(self, paper_uuid: str) -> Optional[Paper]:
        return self.repo.get(paper_uuid)

    def get_by_paper_id(self, paper_id: str) -> Optional[Paper]:
        return self.repo.get_by_paper_id(paper_id)
    
    def get_by_paper_month(
        self,
        month: str,
        sort_by
    ) -> Optional[Paper]:
        return self.repo.get_by_paper_month(month,sort_by)

    def update_paper(self, paper_uuid: str, **fields) -> Optional[Paper]:
        # if "ai_keywords" in fields and fields["ai_keywords"] is None:
        #     fields["ai_keywords"] = []
        # if "meta" in fields and fields["meta"] is None:
        #     fields["meta"] = {}
        return self.repo.update(paper_uuid, **fields)

    def delete_paper(self, paper_uuid: str) -> bool:
        return self.repo.delete(paper_uuid)
