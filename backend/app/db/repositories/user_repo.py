"""Repository for user data access (CRUD)."""
from __future__ import annotations

import uuid
from typing import Iterable, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models.user import User


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self) -> Iterable[User]:
        stmt = select(User).order_by(User.created_at.desc())
        return self.session.scalars(stmt).all()

    def get(self, user_id: str) -> Optional[User]:
        return self.session.get(User, user_id)

    def get_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        return self.session.scalars(stmt).first()

    def create(self, *, email: str, name: str | None = None) -> User:
        entity = User(id=str(uuid.uuid4()), email=email, name=name)
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def update(self, user_id: str, *, name: str | None = None) -> Optional[User]:
        entity = self.get(user_id)
        if not entity:
            return None
        if name is not None:
            entity.name = name
        self.session.commit()
        self.session.refresh(entity)
        return entity

    def delete(self, user_id: str) -> bool:
        entity = self.get(user_id)
        if not entity:
            return False
        self.session.delete(entity)
        self.session.commit()
        return True
