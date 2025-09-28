"""Health check endpoints."""
from __future__ import annotations

from flask import Blueprint

from ...errors import ok
from ...integrations.supabase_client import supabase_ext


bp = Blueprint("health", __name__)


@bp.get("/")
def alive():
    return ok({"status": "ok"})

@bp.get("/supabase")
def supabase_status():
    return ok({
        "anon_initialized": bool(supabase_ext.anon is not None),
        "service_initialized": bool(supabase_ext.service is not None),
    })
