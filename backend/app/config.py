"""Application configuration objects."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class BaseConfig:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me")

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/postgres",
    )
    SQL_ECHO: bool = os.getenv("SQL_ECHO", "false").lower() == "true"
    POOL_SIZE: int = int(os.getenv("POOL_SIZE", 10))
    MAX_OVERFLOW: int = int(os.getenv("MAX_OVERFLOW", 20))

    # Repository backend
    PAPER_REPO_BACKEND: str = os.getenv("PAPER_REPO_BACKEND", "sqlalchemy")

    # Supabase
    SUPABASE_URL: str | None = os.getenv("SUPABASE_URL") or None
    SUPABASE_ANON_KEY: str | None = os.getenv("SUPABASE_ANON_KEY") or None
    SUPABASE_SERVICE_ROLE_KEY: str | None = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or None

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "change-me")
    JWT_ALG: str = os.getenv("JWT_ALG", "HS256")
