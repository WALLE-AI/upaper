"""Builds a minimal OpenAPI spec from existing Pydantic schemas."""
from __future__ import annotations

from typing import Any, Dict
from flask import request, current_app

from ..api.users.schemas import UserCreateIn, UserUpdateIn, UserOut
from ..api.papers.schemas import PaperCreateIn, PaperUpdateIn, PaperOut


def _schemas() -> Dict[str, Any]:
    return {
        "UserCreateIn": UserCreateIn.model_json_schema(ref_template="#/components/schemas/{model}"),
        "UserUpdateIn": UserUpdateIn.model_json_schema(ref_template="#/components/schemas/{model}"),
        "UserOut": UserOut.model_json_schema(ref_template="#/components/schemas/{model}"),
        "PaperCreateIn": PaperCreateIn.model_json_schema(ref_template="#/components/schemas/{model}"),
        "PaperUpdateIn": PaperUpdateIn.model_json_schema(ref_template="#/components/schemas/{model}"),
        "PaperOut": PaperOut.model_json_schema(ref_template="#/components/schemas/{model}"),
    }


def build_openapi() -> Dict[str, Any]:
    base_url = f"{request.scheme}://{request.host}"
    security_schemes = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    return {
        "openapi": "3.0.3",
        "info": {"title": "Backend Starter API", "version": "0.2.0"},
        "servers": [{"url": base_url}],
        "tags": [
            {"name": "Health"},
            {"name": "Users"},
            {"name": "Papers"},
        ],
        "paths": {
            "/api/health/": {
                "get": {"tags": ["Health"], "summary": "Liveness probe", "responses": {"200": {"description": "OK"}}}
            },
            "/api/health/supabase": {
                "get": {"tags": ["Health"], "summary": "Supabase client status", "responses": {"200": {"description": "Status"}}}
            },
            "/api/users/": {
                "get": {"tags": ["Users"], "summary": "List users", "responses": {"200": {"description": "OK"}}},
                "post": {
                    "tags": ["Users"], "summary": "Create user",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/UserCreateIn"}}}},
                    "responses": {"201": {"description": "Created"}}
                }
            },
            "/api/users/{user_id}": {
                "parameters": [{"name": "user_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "get": {"tags": ["Users"], "summary": "Get user by id", "responses": {"200": {"description": "OK"}}},
                "put": {"tags": ["Users"], "summary": "Update user", "responses": {"200": {"description": "OK"}}},
                "delete": {"tags": ["Users"], "summary": "Delete user", "responses": {"200": {"description": "OK"}}}
            },
            "/api/papers/": {
                "get": {"tags": ["Papers"], "summary": "List papers", "responses": {"200": {"description": "OK"}}},
                "post": {
                    "tags": ["Papers"], "summary": "Create paper",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PaperCreateIn"}}}},
                    "responses": {"201": {"description": "Created"}}
                }
            },
            "/api/papers/{paper_uuid}": {
                "parameters": [{"name": "paper_uuid", "in": "path", "required": True, "schema": {"type": "string"}}],
                "get": {"tags": ["Papers"], "summary": "Get paper by uuid", "responses": {"200": {"description": "OK"}}},
                "put": {"tags": ["Papers"], "summary": "Update paper", "responses": {"200": {"description": "OK"}}},
                "delete": {"tags": ["Papers"], "summary": "Delete paper", "responses": {"200": {"description": "OK"}}}
            },
            "/api/papers/by-paper-id/{paper_id}": {
                "parameters": [{"name": "paper_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                "get": {"tags": ["Papers"], "summary": "Get paper by external paper_id", "responses": {"200": {"description": "OK"}}}
            },
            "/api/papers/paper_monthly/{paper_monthly}":{
                "parameters": [{"name": "paper_monthly", "in": "path", "required": True, "schema": {"type": "string"}}],
                "get": {
                    "tags": ["Papers"],
                    "summary": "Fetch daily papers from HuggingFace and create new Paper records (idempotent).",
                    "responses": {
                        "200": {
                            "description": "List of created papers or empty list",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "data": {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/PaperOut"}
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "201": {
                            "description": "Created",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "data": {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/PaperOut"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                
            },
            "/api/papers/daily/paper_daily": {
                "get": {
                    "tags": ["Papers"],
                    "summary": "Fetch daily papers from HuggingFace and create new Paper records (idempotent).",
                    "responses": {
                        "200": {
                            "description": "List of created papers or empty list",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "data": {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/PaperOut"}
                                            }
                                        }
                                    }
                                }
                            }
                        },
                        "201": {
                            "description": "Created",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "data": {
                                                "type": "array",
                                                "items": {"$ref": "#/components/schemas/PaperOut"}
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },

        },
        "components": {
            "schemas": _schemas(),
            "securitySchemes": security_schemes
        },
        # To require auth globally: uncomment next line and add require_bearer to protected routes.
        # "security": [{"BearerAuth": []}]
    }
