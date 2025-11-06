# server.py
# pip install fastapi uvicorn httpx
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse

app = FastAPI()

def _copy_headers(src, dst):
    """
    只拷贝对 PDF 预览有用且安全的响应头；并确保可被 iframe/pdf.js 使用。
    """
    allow_list = [
        "content-type",
        "content-length",
        "accept-ranges",
        "content-range",
        "etag",
        "last-modified",
        "cache-control",
        "content-disposition",  # 有些链接会携带文件名
    ]
    for h in allow_list:
        if h in src:
            dst.headers[h] = src[h]

    # 允许跨域被前端（含 mozilla viewer）读取
    dst.headers["Access-Control-Allow-Origin"] = "*"
    # 辅助某些浏览器跨站资源策略
    dst.headers["Cross-Origin-Resource-Policy"] = "cross-origin"

    # 兜底移除可能阻止内嵌/跨域读取的头（如果存在）
    for bad in ("x-frame-options", "content-security-policy", "x-content-type-options"):
        try:
            del dst.headers[bad]
        except KeyError:
            pass


async def _proxy(method: str, url: str, req: Request):
    # 透传 Range 供分块/跳页
    fwd_headers = {}
    if "range" in req.headers:
        fwd_headers["range"] = req.headers["range"]

    async with httpx.AsyncClient(follow_redirects=True, timeout=None) as client:
        r = await client.request(method, url, headers=fwd_headers)

        if method == "HEAD":
            resp = Response(status_code=r.status_code)
            _copy_headers(r.headers, resp)
            return resp

        async def agen():
            async for chunk in r.aiter_bytes():
                yield chunk

        media = r.headers.get("content-type", "application/pdf")
        resp = StreamingResponse(agen(), status_code=r.status_code, media_type=media)
        _copy_headers(r.headers, resp)
        return resp


@app.get("/pdf")
async def get_pdf(url: str, request: Request):
    return await _proxy("GET", url, request)

@app.head("/pdf")
async def head_pdf(url: str, request: Request):
    return await _proxy("HEAD", url, request)
