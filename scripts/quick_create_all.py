"""Create all tables for a quick dev setup (NOT for production)."""
from __future__ import annotations

from app import create_app
from app.db.session import db
from app.db.base import Base
from app.db.models import user, paper  # noqa: F401


def main() -> None:
    app = create_app()
    with app.app_context():
        assert db.engine is not None
        Base.metadata.create_all(db.engine)
        print("Tables created.")


if __name__ == "__main__":
    main()
