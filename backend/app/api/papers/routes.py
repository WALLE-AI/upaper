"""Papers blueprint (CRUD)."""
from __future__ import annotations

import json
import time
from typing import Dict, Iterable, List, Optional
import uuid
from ...services.file_service import FileService
from flask import Blueprint, Response, request, stream_with_context
from sqlalchemy.orm import Session

from ...utils.get_hf_papers import get_hugging_face_top_daily_paper

from ...db.session import db
from ...errors import ok
from ...services.paper_service import PaperService
from ...domain.paper import Paper
from .schemas import PaperCreateIn, PaperUpdateIn, PaperOut
from dataclasses import asdict
from ...services.llm_service import llm_service


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


def maybe_make_paper(item: dict) -> Paper | None:
    p = item if isinstance(item, dict) else None
    if not isinstance(p, dict):
        return
    title = p.get("title") or p.get("name") or ""
    if not title:
        return
    paper_id = p.get("id") or p.get("_id")
    votes = p.get("upvotes") or p.get("upvotes") or None
    source_url = p.get("url") or p.get("sourceUrl") or p.get("arxivUrl")
    hf_url = p.get("slug")

    date_str = p.get("publishedAt")
    ai_keywords=p.get("ai_keywords") or []
    ai_summary=p.get("ai_summary") or ""
    
    if not p.get("summary_zh"):
        summary = p.get('summary') if isinstance(p, dict) and p.get('summary') else ""
        summary_translate=llm_service.get_paper_translate(summary)
        p["summary_zh"] = summary_translate
        
    if not p.get("ai_summary_zh"):
        ai_summary = p.get("ai_summary") or ""
        ai_summary_translate = llm_service.get_paper_translate(ai_summary)
        p["ai_summary_zh"] = ai_summary_translate 
    
    return Paper(
        id=str(uuid.uuid4()),
        title=title,
        source_url=source_url,
        huggingface_url=hf_url,
        date_str=date_str,
        ai_keywords=ai_keywords,
        ai_summary=ai_summary,
        paper_id=str(paper_id) if p.get("id") or p.get("_id") is not None else None,
        votes=int(votes) if isinstance(votes, int) else None,
        month_url="",
        meta=p
    )
    
    
def translate_summary_and_ai_summary_to_update(paper:dict,svc)->dict:
    p = PaperOut.model_validate(asdict(paper)).model_dump()
    if not p.get("meta").get("summary_zh"):
        summary = p.get("meta").get('summary') if p.get("meta") and isinstance(p.get("meta"), dict) and p.get("meta").get('summary') else ""
        summary_translate=llm_service.get_paper_translate(summary)
        p["meta"]["summary_zh"] = summary_translate
        print("update paper summary:",p.get("id"))
        svc.update_paper(paper_uuid=p.get("id"),**p)
    if not p.get("meta").get("ai_summary_zh"):
        ai_summary = p.get("ai_summary") or ""
        ai_summary_translate = llm_service.get_paper_translate(ai_summary)
        p["meta"]["ai_summary_zh"] = ai_summary_translate
        print("update paper ai summary:",p.get("id"))
        svc.update_paper(paper_uuid=p.get("id"),**p)
    return p

@bp.get("/daily/paper_daily")
def get_daily_paper():
    """
    Fetch the top huggingface daily papers for a given daily identifier and create new Paper entries.

    Path parameter:
      - paper_daily: an identifier for the daily list (e.g. "2025-09-28" or "2025-09")
    """
    # 1) call your HF fetcher (must return iterable of dict-like meta)
    paper_list = get_hugging_face_top_daily_paper()  # <-- pass the param if needed

    svc = _service()
    created_items: List[dict] = []

    for paper_meta in paper_list:
        paper_id = paper_meta.get("id") or paper_meta.get("_id")
        if not paper_id:
            continue

        # 先检查是否存在（按外部 paper_id）
        existing = svc.get_by_paper_id(str(paper_id))
        if existing:
            continue
        ##翻译摘要和AI摘要,并且插入数据库中
        
        p = maybe_make_paper(paper_meta)
        if not p:
            continue
        print("Creating paper:", p.title)
        created = svc.create_paper(p)
        created_items.append(PaperOut.model_validate(asdict(created)).model_dump())
    return ok(len(created_items), 201 if created_items else 200)


@bp.post("/analyze-stream")
def paper_analyze():
    """
    Fetch the top huggingface daily papers for a given daily identifier and create new Paper entries.
    """
    print("interface success")
    return ok({"status": "ok"})


@bp.get("/search/paper-search")
def paper_search(query:str,limit:int=10):
    """
    Fetch the top huggingface daily papers for a given daily identifier and create new Paper entries.
    """
    print(query)
    return ok({"status": "ok"})

@bp.post("/paper-chat/stream")
def paper_chat():
    """
    Fetch the top huggingface daily papers for a given daily identifier and create new Paper entries.
    """
    print("interface success")
    return ok({"status": "ok"})

                


@bp.post("/translate-stream")
def paper_translate():
    # """
    # Fetch the top huggingface daily papers for a given daily identifier and create new Paper entries.
    # """
    # print("interface success")
    # return ok({"status": "ok"})
    """
    流式返回论文标题/摘要的翻译文本。
    前端示例：fetch(..., { body: JSON.stringify({ paper, targetLanguage }) })
             -> response.body.getReader() 按块解码。
    """
    try:
        payload = request.get_json(force=True, silent=False)
    except Exception:
        return Response(
            json.dumps({"error": "Invalid JSON body"}),
            status=400,
            mimetype="application/json",
        )

    if not isinstance(payload, dict):
        return Response(
            json.dumps({"error": "Request body must be a JSON object"}),
            status=400,
            mimetype="application/json",
        )

    paper = payload.get("paper") or {}
    target_lang = payload.get("targetLanguage") or "zh"

    if not isinstance(paper, dict):
        return Response(
            json.dumps({"error": "`paper` must be an object"}),
            status=400,
            mimetype="application/json",
        )

    # 可通过 query/body 控制是否强制使用 mock（便于联调）
    force_mock = False
    if isinstance(payload.get("mock"), bool):
        force_mock = payload["mock"]
    elif request.args.get("mock") in {"1", "true", "True"}:
        force_mock = True

    try:
        gen: Iterable[str]
        if force_mock:
            gen = FileService._iter_mock_translation(paper, target_lang)
        else:
            gen = FileService._iter_real_translation(paper, target_lang)

        # 可选：设置心跳间隔（秒）。如后面有 nginx / cloudflare，可设 10~15s。
        heartbeat_every = None  # 例如 15.0

        resp = Response(
            stream_with_context(FileService._as_plain_text_stream(gen, heartbeat_interval_s=heartbeat_every)),
            # **与前端匹配**：纯文本流，而非 text/event-stream
            mimetype="text/plain; charset=utf-8",
        )
        # 重要：禁用反向代理缓冲，确保“边生成边发送”
        resp.headers["X-Accel-Buffering"] = "no"        # nginx
        resp.headers["Cache-Control"] = "no-cache"
        resp.headers["Connection"] = "keep-alive"
        # CORS 如全局没配，这里可临时放开（按需收紧域名）
        resp.headers.setdefault("Access-Control-Allow-Origin", "*")
        return resp

    except Exception as e:
        print("translate-stream failed")
        return Response(
            json.dumps({"error": f"Internal error: {type(e).__name__}: {str(e)}"}),
            status=500,
            mimetype="application/json",
        )


@bp.post("/interpret-stream")
def paper_interpret():
    """
    Fetch the top huggingface daily papers for a given daily identifier and create new Paper entries.
    """
    print("interface success")
    return ok({"status": "ok"})




@bp.get("/paper_monthly/<paper_monthly>")
def get_month_paper(paper_monthly: str):
    """
    Fetch the top huggingface daily papers for a given daily identifier and create new Paper entries.

    Path parameter:
      - paper_daily: an identifier for the daily list (e.g. "2025-09" or "2025-08")
    """
    # 1) call your HF fetcher (must return iterable of dict-like meta)
    svc = _service()
    created_items: List[dict] = []

    # Query parameters
    sort_by = request.args.get("sort_by")  # e.g. likes_desc, likes_asc, created_at_desc
    page = int(request.args.get("page", "1"))
    limit = int(request.args.get("limit", "20"))
    # Support both Chinese key and English fallback
    source = request.args.get("论文来源") or request.args.get("source")

    papers = svc.get_by_paper_month(
        str(paper_monthly),sort_by
    )
    for index,paper in enumerate(papers):
        ##翻译摘要和AI摘要,并且插入数据库中
        p = translate_summary_and_ai_summary_to_update(paper,svc)
        created_items.append(p)
    return ok(created_items, 201 if created_items else 200)

@bp.get("/filter")
def get_filter_paper():
    """
    Fetch the top huggingface daily papers for a given daily identifier and create new Paper entries.

    Path parameter:
      - paper_daily: an identifier for the daily list (e.g. "2025-09" or "2025-08")
    """
    # 1) call your HF fetcher (must return iterable of dict-like meta)
    return ok({"status": "ok"})


@bp.get("/paper_uuid/<paper_uuid>")
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
    ##下载pdf
    path,pid_dir = FileService.download_file(paper_id)
    md_content = FileService.parser_file(file_path=path,file_name_dir=pid_dir,parser_type="mineru")
    print("md_content length:",len(md_content))
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
