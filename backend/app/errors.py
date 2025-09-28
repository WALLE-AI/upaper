"""Global HTTP error handling and JSON response helpers."""
from __future__ import annotations

from typing import Any

from flask import Flask, jsonify


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(400)
    def bad_request(err: Exception):  # type: ignore[override]
        return jsonify({"error": "bad_request", "message": str(err)}), 400

    @app.errorhandler(404)
    def not_found(err: Exception):  # type: ignore[override]
        return jsonify({"error": "not_found", "message": str(err)}), 404

    @app.errorhandler(422)
    def unprocessable(err: Exception):  # type: ignore[override]
        return jsonify({"error": "unprocessable_entity", "message": str(err)}), 422

    @app.errorhandler(500)
    def internal(err: Exception):  # type: ignore[override]
        return jsonify({"error": "internal_server_error", "message": "unexpected error"}), 500


def ok(data: Any, status: int = 200):
    return jsonify({"data": data}), status
