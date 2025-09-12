# PaperScope FastAPI Backend

一个可直接联调的 FastAPI 后端，提供 `GET /papers` 接口，支持搜索、来源与标签过滤、分页。
前端（Next.js 项目）把请求发到自己的 `/api/papers` 代理，再由代理转发到此后端。

## 快速开始
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# 可选：cp .env.example .env && 编辑 FRONTEND_ORIGIN
uvicorn app.main:app --reload --port 8000
# 浏览器打开 http://127.0.0.1:8000/docs 进行联调
```

## API
### GET /papers
查询参数：
- `search`: string（标题/摘要模糊）
- `sources`: 逗号分隔（如 `HF,arXiv`）
- `tags`: 逗号分隔
- `page`: int，默认 1
- `page_size`: int，默认 20

返回示例：
```json
{
  "items": [
    {
      "id": "p1",
      "title": "Sharing is Caring...",
      "summary": "Post-training language models...",
      "source": "HF",
      "likes": 194,
      "comments": 24,
      "tags": ["Reinforcement-Learning", "Agent", "Reasoning"],
      "aiNotes": ["AT 解析(6个模型)"],
      "badges": ["Intern-S1", "GLM4.5"]
    }
  ],
  "total": 63
}
```

### 健康检查
`GET /health` → `{ "ok": true }`

## 与前端联调
前端 `.env.local` 设置：
```
API_BASE_URL=http://127.0.0.1:8000
```
Next.js 开发启动后，访问 `http://localhost:3000`，搜索与筛选都应生效。

## 测试用例
```bash
# 取第一页
curl "http://127.0.0.1:8000/papers?page=1&page_size=5"

# 搜索
curl "http://127.0.0.1:8000/papers?search=Reasoning&page=1&page_size=5"

# 来源+标签过滤
curl "http://127.0.0.1:8000/papers?sources=HF,arXiv&tags=Agent,Reasoning&page=1&page_size=5"
```
