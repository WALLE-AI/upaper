from __future__ import annotations
from fastapi import FastAPI, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List

from app.models import Paper, PaperListResp

import os
from dotenv import load_dotenv

from app.data import get_hf_daily_papers
load_dotenv()

app = FastAPI(title="PaperScope Backend", version="1.0.0")

# 如需浏览器直连后端，可开启 CORS（联调走 Next 代理通常不需要）
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin, "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/papers", response_model=PaperListResp)
def list_papers(
    search: Optional[str] = Query(None, description="关键字，支持标题/摘要模糊查询"),
    sources: Optional[str] = Query(None, description="逗号分隔的来源，如 HF,arXiv"),
    tags: Optional[str] = Query(None, description="逗号分隔的标签"),
    page: int = Query(1, ge=1, description="页码（从 1 开始）"),
    page_size: int = Query(20, ge=1, le=100, description="每页条数")
):
    # 1) 数据准备
    data = get_hf_daily_papers()

    # 2) 搜索过滤（标题或摘要）
    if search:
        s = search.strip().lower()
        data = [p for p in data if s in p["title"].lower() or s in p["summary"].lower()]

    # 3) 来源过滤
    if sources:
        allowed = {x.strip() for x in sources.split(",") if x.strip()}
        data = [p for p in data if p.get("source") in allowed]

    # 4) 标签过滤（取交集）
    if tags:
        wanted = {x.strip() for x in tags.split(",") if x.strip()}
        data = [p for p in data if wanted.intersection(set(p.get("tags", [])))]

    total = len(data)

    # 5) 分页
    start = (page - 1) * page_size
    end = start + page_size
    page_items = data[start:end]

    # 6) 返回
    return PaperListResp(items=[Paper(**p) for p in page_items], total=total)
