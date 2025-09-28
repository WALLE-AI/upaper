"""SQLAlchemy engine/session initialization and lifecycle management."""
from __future__ import annotations

from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker


class Database:
    def __init__(self) -> None:
        self.engine = None
        self.Session = None  # type: ignore[assignment]

    def init_app(self, app: Flask) -> None:
        url: str = app.config["DATABASE_URL"]
        echo: bool = app.config.get("SQL_ECHO", False)
        pool_size: int = app.config.get("POOL_SIZE", 10)
        max_overflow: int = app.config.get("MAX_OVERFLOW", 20)

        self.engine = create_engine(
            url,
            echo=echo,
            pool_pre_ping=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
            future=True,
        )
        self.Session = scoped_session(
            sessionmaker(bind=self.engine, expire_on_commit=False, autoflush=False, future=True)
        )

        @app.teardown_appcontext
        def remove_session(_: object | None) -> None:
            if self.Session is not None:
                self.Session.remove()


db = Database()
