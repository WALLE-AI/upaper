# PaperScope Next (REST API 版)

## 使用
1. 复制 `.env.local.example` 为 `.env.local` 并设置：
```
API_BASE_URL=https://your-backend.example.com
# API_TOKEN=xxxx
```
2. 安装依赖：`npm i`
3. 开发：`npm run dev`  → http://localhost:3000

## 数据流
前端页面 -> `/api/papers` (Next.js 代理) -> `${API_BASE_URL}/papers` (你的后端)

### 查询参数（前端 -> 后端）
- `search`: string
- `sources`: 逗号分隔，如 `HF,arXiv`
- `tags`: 逗号分隔
- `page`: 页码（默认 1） → 转发为 `page`
- `pageSize`: 每页数量（默认 20） → 转发为 `page_size`

### 后端响应结构示例
```json
{ "items": [ { "id":"p1", "title":"...", "summary":"...", "source":"HF", "likes":100, "comments":2, "tags":["Agent"] } ], "total": 63 }
```
