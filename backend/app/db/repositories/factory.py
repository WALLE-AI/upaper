"""Repository factory for Paper (sqlalchemy|supabase)."""
from __future__ import annotations

from typing import Optional

from flask import current_app
from sqlalchemy.orm import Session

from .paper_repo import PaperRepository as SQLARepo
from .paper_repo_supabase import PaperRepositorySupabase
from ...integrations.supabase_client import supabase_ext


def paper_repo(session: Optional[Session] = None):
    backend = (current_app.config.get("PAPER_REPO_BACKEND") or "sqlalchemy").lower()
    if backend == "supabase":
        client = supabase_ext.service or supabase_ext.anon
        if client is None:
            raise RuntimeError("Supabase client is not initialized; set SUPABASE_URL and a key.")
        return PaperRepositorySupabase(client)
    if session is None:
        raise RuntimeError("SQLAlchemy repo requires a session")
    return SQLARepo(session)
