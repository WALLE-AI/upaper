"""Docs blueprint: /openapi.json, /docs (Swagger UI), /redoc."""
from __future__ import annotations

from flask import Blueprint, Response, jsonify

from .openapi import build_openapi

bp = Blueprint("docs", __name__)


@bp.get("/openapi.json")
def openapi_json() -> Response:
    spec = build_openapi()
    return jsonify(spec)


@bp.get("/docs")
def swagger_ui() -> Response:
    html = """

    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8"/>
      <title>API Docs</title>
      <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
      <style>body{margin:0;} #swagger-ui{height:100vh;}</style>
    </head>
    <body>
      <div id="swagger-ui"></div>
      <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
      <script>window.ui = SwaggerUIBundle({ url: '/openapi.json', dom_id: '#swagger-ui' });</script>
    </body>
    </html>
    """
    return Response(html, mimetype="text/html")


@bp.get("/redoc")
def redoc() -> Response:
    html = """

    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8"/>
      <title>ReDoc</title>
      <style>body{margin:0;} #redoc{height:100vh;}</style>
      <script src="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js"></script>
    </head>
    <body>
      <redoc spec-url="/openapi.json"></redoc>
    </body>
    </html>
    """
    return Response(html, mimetype="text/html")
