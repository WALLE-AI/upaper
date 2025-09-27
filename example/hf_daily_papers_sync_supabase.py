\
import argparse
import datetime as dt
import html
import json
import os
import random
import re
import threading
import time
from dataclasses import dataclass, asdict
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client


BASE = "https://huggingface.co"
MONTH_URL_TMPL = BASE + "/papers/month/{yyyy}-{mm:02d}"
ROBOTS_URL = BASE + "/robots.txt"
CACHE_DIR = "./cache/month"

class TokenBucketRateLimiter:
    def __init__(self, rate: float, burst: int):
        self.rate = max(0.01, rate)
        self.burst = max(1, burst)
        self._tokens = float(self.burst)
        self._last = time.monotonic()
        self._lock = threading.Lock()

    def wait(self):
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last
            self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
            if self._tokens < 1.0:
                need = 1.0 - self._tokens
                sleep_s = need / self.rate
                self._lock.release()
                try:
                    time.sleep(sleep_s)
                finally:
                    self._lock.acquire()
                self._tokens = 0.0
                self._last = time.monotonic()
                return
            else:
                self._tokens -= 1.0
                self._last = now

def build_session(user_agent: Optional[str] = None) -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=5, read=5, connect=5, backoff_factor=1.2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD"}),
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({
        "User-Agent": user_agent or "HF-DailyPapers-Crawler/1.0 (+respectful; contact: you@example.com)"
    })
    return s

def can_fetch(path: str, user_agent: str) -> bool:
    try:
        rp = RobotFileParser()
        rp.set_url(ROBOTS_URL)
        rp.read()
        return rp.can_fetch(user_agent, path)
    except Exception:
        return True

def month_range(start: dt.date, end: dt.date):
    y, m = start.year, start.month
    while (y < end.year) or (y == end.year and m <= end.month):
        yield y, m
        if m == 12:
            y += 1; m = 1
        else:
            m += 1

def cache_path(year: int, month: int) -> str:
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{year}-{month:02d}.html")

def read_cache(year: int, month: int) -> Optional[bytes]:
    p = cache_path(year, month)
    if os.path.exists(p):
        with open(p, "rb") as f:
            return f.read()
    return None

def write_cache(year: int, month: int, content: bytes) -> None:
    with open(cache_path(year, month), "wb") as f:
        f.write(content)

@dataclass
class Paper:
    title: str
    source_url: Optional[str]
    huggingface_url: Optional[str]
    date_str: Optional[str]
    paper_id: Optional[str]
    votes: Optional[int]
    ai_keywords: List[str]
    ai_summary: str
    month_url: str
    meta: Dict

def parse_month_page(html_bytes: bytes, month_url: str) -> List[Paper]:
    soup = BeautifulSoup(html_bytes, "html.parser")
    found: List[Paper] = []
    containers = soup.find_all(attrs={"data-props": True})
    for c in containers:
        raw = c.get("data-props", "")
        if not raw:
            continue
        try:
            data = json.loads(html.unescape(raw))
        except Exception:
            continue
        found.extend(extract_papers_from_json(data, month_url))

    if not found:
        for a in soup.select('a[href^="/papers/"]'):
            href = a.get("href") or ""
            if not href:
                continue
            full = urljoin(BASE, href)
            title = a.get_text(strip=True) or None
            if title:
                found.append(Paper(
                    title=title,
                    source_url=None,
                    huggingface_url=full,
                    date_str=None,
                    paper_id=None,
                    votes=None,
                    ai_keywords=None,
                    ai_summary=None,
                    month_url=month_url,
                    meta={"fallback": True}
                ))
    return found

def extract_papers_from_json(obj, month_url: str) -> List[Paper]:
    collected: List[Paper] = []

    def maybe_make_paper(item: dict, ctx: dict):
        p = item.get("paper") if isinstance(item, dict) else None
        if not isinstance(p, dict):
            return
        title = p.get("title") or p.get("name") or ""
        if not title:
            return
        paper_id = p.get("id") or p.get("_id")
        votes = p.get("upvotes") or p.get("upvotes") or None
        source_url = p.get("url") or p.get("sourceUrl") or p.get("arxivUrl")
        hf_url = p.get("slug")
        if hf_url and hf_url.startswith("/"):
            hf_url = urljoin(BASE, hf_url)
        date_str = p.get("publishedAt") or ctx.get("publishedAt")
        ai_keywords=p.get("ai_keywords") or []
        ai_summary=p.get("ai_summary") or ""
        collected.append(Paper(
            title=title,
            source_url=source_url,
            huggingface_url=hf_url,
            date_str=date_str,
            ai_keywords=ai_keywords,
            ai_summary=ai_summary,
            paper_id=str(paper_id) if p.get("id") or p.get("_id") is not None else None,
            votes=int(votes) if isinstance(votes, int) else None,
            month_url=month_url,
            meta=p
        ))

    def walk(x, ctx):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in ("dailyPapers", "papers", "calendarPapers", "topPapers"):
                    if isinstance(v, list):
                        for it in v:
                            if isinstance(it, dict):
                                maybe_make_paper(it, ctx)
                                walk(it, ctx)
                if k == "date" and isinstance(v, str) and re.match(r"\d{4}-\d{2}-\d{2}", v):
                    ctx = {**ctx, "date": v}
                walk(v, ctx)
        elif isinstance(x, list):
            for i in x:
                walk(i, ctx)

    walk(obj, {})
    return collected

def fetch_month(year: int, month: int, session: requests.Session,
                limiter: TokenBucketRateLimiter, jitter: float, user_agent: str) -> Tuple[Tuple[int, int], Optional[bytes], Optional[str]]:
    url = MONTH_URL_TMPL.format(yyyy=year, mm=month)
    cache = read_cache(year, month)
    if cache:
        return (year, month), cache, url

    path = f"/papers/month/{year}-{month:02d}"
    if not can_fetch(path, user_agent):
        print(f"[robots] Disallowed: {path}")
        return (year, month), None, url

    limiter.wait()
    if jitter > 0:
        time.sleep(random.uniform(0, jitter))

    try:
        r = session.get(url, timeout=15)
        r.raise_for_status()
        content = r.content
        write_cache(year, month, content)
        return (year, month), content, url
    except requests.RequestException as e:
        print(f"[error] Fetch {url} failed: {e}")
        return (year, month), None, url

def get_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY/ANON_KEY")
    return create_client(url, key)

def to_row(p: Paper) -> Dict:
    d = None
    if p.date_str and re.match(r"^\d{4}-\d{2}-\d{2}$", p.date_str):
        d = p.date_str
    return {
        "paper_id": p.paper_id,
        "title": p.title,
        "source_url": p.source_url,
        "huggingface_url": p.huggingface_url,
        "date": p.date_str,
        "month_url": p.month_url,
        "ai_keywords":p.ai_keywords,
        "ai_summary": p.ai_summary,
        "votes": p.votes,
        "meta": p.meta or {},
    }

def chunked(iterable, size=500):
    buf = []
    for x in iterable:
        buf.append(x)
        if len(buf) >= size:
            yield buf
            buf = []
    if buf:
        yield buf

def upsert_papers(rows: List[Dict], table="daily_papers"):
    sb = get_supabase()
    with_id = [r for r in rows if r.get("paper_id")]
    without_id = [r for r in rows if not r.get("paper_id")]

    for batch in chunked(with_id, 500):
        sb.table(table).upsert(batch, on_conflict="paper_id").execute()

    for batch in chunked(without_id, 500):
        sb.table(table).upsert(batch, on_conflict="title,source_url").execute()

def query_papers(title_like: Optional[str] = None, date_from: Optional[str] = None,
                 date_to: Optional[str] = None, limit: int = 50, table="daily_papers") -> List[Dict]:
    sb = get_supabase()
    q = sb.table(table).select("*").order("date", desc=True).limit(limit)
    if title_like:
        q = q.ilike("title", f"%{title_like}%")
    if date_from:
        q = q.gte("date", date_from)
    if date_to:
        q = q.lte("date", date_to)
    return q.execute().data or []

def update_paper_by_id(row_id: str, patch: Dict, table="daily_papers") -> Dict:
    sb = get_supabase()
    return sb.table(table).update(patch).eq("id", row_id).execute().data or {}

def insert_one(p: Paper, table="daily_papers") -> Dict:
    sb = get_supabase()
    row = to_row(p)
    if row.get("paper_id"):
        return sb.table(table).upsert(row, on_conflict="paper_id").execute().data or {}
    else:
        return sb.table(table).upsert(row, on_conflict="title,source_url").execute().data or {}

def crawl_and_sync(start_month: str, end_month: Optional[str], rate: float = 0.5,
                   burst: int = 1, jitter: float = 0.2, user_agent: Optional[str] = None):
    start_y, start_m = map(int, start_month.split("-"))
    start = dt.date(start_y, start_m, 1)
    if end_month:
        end_y, end_m = map(int, end_month.split("-"))
        end = dt.date(end_y, end_m, 1)
    else:
        today = dt.date.today()
        end = dt.date(today.year, today.month, 1)

    ua = user_agent or "HF-DailyPapers-Crawler/1.0 (+respectful; contact: you@example.com)"
    session = build_session(ua)
    limiter = TokenBucketRateLimiter(rate=rate, burst=burst)

    all_papers: List[Paper] = []
    for (y, m) in month_range(start, end):
        (yy, mm), html_bytes, url = fetch_month(y, m, session, limiter, jitter, ua)
        if not html_bytes:
            continue
        papers = parse_month_page(html_bytes, url)
        print(f"[info] {yy}-{mm:02d}: parsed {len(papers)} items")
        all_papers.extend(papers)

    seen = set()
    unique: List[Paper] = []
    for p in all_papers:
        key = p.paper_id or f"{p.title}::{p.source_url or ''}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(p)

    rows = [to_row(p) for p in unique]
    upsert_papers(rows)
    print(f"[done] upserted {len(rows)} rows into Supabase")

def main():
    ap = argparse.ArgumentParser(description="HF Daily Papers: crawl & sync to Supabase; query/update helpers.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("sync", help="Crawl from start to end month and upsert into Supabase")
    s1.add_argument("--start", required=False,type=str,default="2023-05", help="YYYY-MM, e.g. 2023-05")
    s1.add_argument("--end", type=str,help="YYYY-MM, default = current month")
    s1.add_argument("--rate", type=float, default=0.5, help="requests per second (global)")
    s1.add_argument("--burst", type=int, default=1, help="token bucket burst")
    s1.add_argument("--jitter", type=float, default=0.2, help="random jitter seconds per request")
    s1.add_argument("--user-agent", default=None)

    s2 = sub.add_parser("query", help="Query papers from Supabase")
    s2.add_argument("--title-like", help="ILIKE title")
    s2.add_argument("--from", dest="date_from", help="YYYY-MM-DD")
    s2.add_argument("--to", dest="date_to", help="YYYY-MM-DD")
    s2.add_argument("--limit", type=int, default=50)

    s3 = sub.add_parser("update", help="Update one row by id")
    s3.add_argument("--id", required=True, help="row id (uuid)")
    s3.add_argument("--votes", type=int)
    s3.add_argument("--title")
    s3.add_argument("--source-url")
    s3.add_argument("--hf-url")
    s3.add_argument("--date")

    args = ap.parse_args()

    if args.cmd == "sync":
        crawl_and_sync(
            start_month=args.start,
            end_month=args.end,
            rate=args.rate,
            burst=args.burst,
            jitter=args.jitter,
            user_agent=args.user_agent
        )
    elif args.cmd == "query":
        rows = query_papers(
            title_like=args.title_like,
            date_from=args.date_from,
            date_to=args.date_to,
            limit=args.limit
        )
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    elif args.cmd == "update":
        patch = {}
        if args.votes is not None: patch["votes"] = args.votes
        if args.title: patch["title"] = args.title
        if args.source_url: patch["source_url"] = args.source_url
        if args.hf_url: patch["huggingface_url"] = args.hf_url
        if args.date: patch["date"] = args.date
        if not patch:
            raise SystemExit("No fields to update")
        res = update_paper_by_id(args.id, patch)
        print(json.dumps(res, ensure_ascii=False, indent=2))
        
        
'''
python hf_daily_papers_sync.py sync --start 2023-05

# 更快一些（仍然很克制）
python hf_daily_papers_sync.py sync --start 2023-05 --rate 0.8 --burst 2 --jitter 0.3

# 查近 50 条
python hf_daily_papers_sync.py query

# 标题模糊查
python hf_daily_papers_sync.py query --title-like "diffusion"

# 按日期范围
python hf_daily_papers_sync.py query --from 2024-01-01 --to 2024-12-31 --limit 200


'''

if __name__ == "__main__":
    main()
