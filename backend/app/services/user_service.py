"""User service encapsulating business rules."""
from __future__ import annotations

from typing import Iterable, Optional

from sqlalchemy.orm import Session

from ..db.repositories.user_repo import UserRepository
from ..db.models.user import User


class UserService:
    def __init__(self, session: Session) -> None:
        self.repo = UserRepository(session)

    def list_users(self) -> Iterable[User]:
        return self.repo.list()

    def create_user(self, email: str, name: str | None = None) -> User:
        if self.repo.get_by_email(email):
            raise ValueError("email already exists")
        return self.repo.create(email=email, name=name)

    def get_user(self, user_id: str) -> Optional[User]:
        return self.repo.get(user_id)

    def update_user(self, user_id: str, name: str | None) -> Optional[User]:
        return self.repo.update(user_id, name=name)

    def delete_user(self, user_id: str) -> bool:
        return self.repo.delete(user_id)
