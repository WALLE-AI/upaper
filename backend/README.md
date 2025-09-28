# Flask + SQLAlchemy + Supabase Switch + OpenAPI Docs + JWT

A production-friendly starter:
- Flask Blueprints with layered architecture (API → Service → Repository → Model)
- SQLAlchemy (PostgreSQL/Supabase, MySQL) **or** Supabase PostgREST via env switch
- Pydantic v2 request/response models
- OpenAPI at `/openapi.json` + Swagger UI `/docs` + ReDoc `/redoc`
- Optional JWT utilities (Bearer) for protected routes

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e .
cp .env.example .env
flask --app app.wsgi run --debug
```

Health: `GET /api/health/`  
Docs: `/docs` and `/redoc`

### Choose repository backend
```
PAPER_REPO_BACKEND=sqlalchemy  # default; uses DATABASE_URL via SQLAlchemy
# PAPER_REPO_BACKEND=supabase   # uses supabase-py (PostgREST)
```

### Supabase
Provide at least:
```
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...   # server-side (bypass RLS) recommended
# or SUPABASE_ANON_KEY=...      # RLS applies
```
Health probe: `GET /api/health/supabase`

### JWT (optional)
```
JWT_SECRET=change-me
JWT_ALG=HS256
```
Use `from app.auth.jwt import require_bearer` to protect endpoints.

### Create tables quickly (dev only)
```bash
python scripts/quick_create_all.py
```

---

## API Documentation
- OpenAPI JSON: `GET /openapi.json`
- Swagger UI:   `GET /docs`
- ReDoc:        `GET /redoc`

The spec is assembled from Pydantic schemas so it stays in sync with payloads.
