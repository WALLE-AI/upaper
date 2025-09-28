"""Papers blueprint (CRUD)."""
from __future__ import annotations

import uuid
from flask import Blueprint, request
from sqlalchemy.orm import Session

from ...db.session import db
from ...errors import ok
from ...services.paper_service import PaperService
from ...domain.paper import Paper
from .schemas import PaperCreateIn, PaperUpdateIn, PaperOut
from dataclasses import asdict


bp = Blueprint("papers", __name__)


def _service() -> PaperService:
    assert db.Session is not None, "DB session is not initialized"
    session: Session = db.Session()
    return PaperService(session)


@bp.get("/")
def list_papers():
    month_url = request.args.get("month_url")
    limit = int(request.args.get("limit", "200"))
    svc = _service()
    items = [PaperOut.model_validate(asdict(p)).model_dump() for p in svc.list_papers(month_url, limit)]
    return ok(items)


@bp.post("/")
def create_paper():
    payload = PaperCreateIn.model_validate_json(request.data)
    svc = _service()
    p = Paper(
        id=str(uuid.uuid4()),
        title=payload.title,
        month_url=payload.month_url,
        source_url=payload.source_url,
        huggingface_url=payload.huggingface_url,
        date_str=payload.date_str,
        paper_id=payload.paper_id,
        votes=payload.votes,
        ai_keywords=payload.ai_keywords or [],
        ai_summary=payload.ai_summary or "",
        meta=payload.meta or {},
    )
    created = svc.create_paper(p)
    return ok(PaperOut.model_validate(asdict(p)).model_dump(), 201)


@bp.get("/<paper_uuid>")
def get_paper(paper_uuid: str):
    svc = _service()
    p = svc.get_paper(paper_uuid)
    if not p:
        return ok(None, 404)
    return ok(PaperOut.model_validate(asdict(p)).model_dump())

@bp.get("/by-paper-id/<paper_id>")
def get_by_paper_id(paper_id: str):
    svc = _service()
    p = svc.get_by_paper_id(paper_id)
    if not p:
        return ok(None, 404)
    return ok(PaperOut.model_validate(asdict(p)).model_dump())


@bp.put("/<paper_uuid>")
def update_paper(paper_uuid: str):
    payload = PaperUpdateIn.model_validate_json(request.data)
    svc = _service()
    fields = {k: v for k, v in payload.model_dump().items() if v is not None}
    p = svc.update_paper(paper_uuid, **fields)
    if not p:
        return ok(None, 404)
    return ok(PaperOut.model_validate(asdict(p)).model_dump())


@bp.delete("/<paper_uuid>")
def delete_paper(paper_uuid: str):
    svc = _service()
    ok_ = svc.delete_paper(paper_uuid)
    return ok({"deleted": ok_})
