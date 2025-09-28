"""Minimal JWT helpers and a Flask decorator for Bearer auth (optional)."""
from __future__ import annotations

import functools
from typing import Any, Callable, Dict, Optional

import jwt
from flask import current_app, request, jsonify


def encode(payload: Dict[str, Any]) -> str:
    secret = current_app.config.get("JWT_SECRET", "change-me")
    alg = current_app.config.get("JWT_ALG", "HS256")
    return jwt.encode(payload, secret, algorithm=alg)


def decode(token: str) -> Dict[str, Any]:
    secret = current_app.config.get("JWT_SECRET", "change-me")
    alg = current_app.config.get("JWT_ALG", "HS256")
    return jwt.decode(token, secret, algorithms=[alg])


def require_bearer(fn: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "unauthorized", "message": "Missing Bearer token"}), 401
        token = auth.split(" ", 1)[1]
        try:
            request.jwt = decode(token)  # type: ignore[attr-defined]
        except Exception as e:  # pragma: no cover - short path
            return jsonify({"error": "unauthorized", "message": str(e)}), 401
        return fn(*args, **kwargs)
    return wrapper
