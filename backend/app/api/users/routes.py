"""Users blueprint (CRUD)."""
from __future__ import annotations

from flask import Blueprint, request
from sqlalchemy.orm import Session

from ...db.session import db
from ...errors import ok
from ...services.user_service import UserService
from .schemas import UserCreateIn, UserUpdateIn, UserOut


bp = Blueprint("users", __name__)


def _service() -> UserService:
    assert db.Session is not None, "DB session is not initialized"
    session: Session = db.Session()
    return UserService(session)


@bp.get("/")
def list_users():
    svc = _service()
    items = [{"id": u.id, "email": u.email, "name": u.name} for u in svc.list_users()]
    return ok(items)


@bp.post("/")
def create_user():
    payload = UserCreateIn.model_validate_json(request.data)
    svc = _service()
    user = svc.create_user(email=payload.email, name=payload.name)
    return ok({"id": user.id, "email": user.email, "name": user.name}, 201)


@bp.get("/<user_id>")
def get_user(user_id: str):
    svc = _service()
    user = svc.get_user(user_id)
    if not user:
        return ok(None, 404)
    return ok({"id": user.id, "email": user.email, "name": user.name})


@bp.put("/<user_id>")
def update_user(user_id: str):
    payload = UserUpdateIn.model_validate_json(request.data)
    svc = _service()
    user = svc.update_user(user_id, name=payload.name)
    if not user:
        return ok(None, 404)
    return ok({"id": user.id, "email": user.email, "name": user.name})


@bp.delete("/<user_id>")
def delete_user(user_id: str):
    svc = _service()
    ok_ = svc.delete_user(user_id)
    return ok({"deleted": ok_})
