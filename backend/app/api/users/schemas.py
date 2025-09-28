"""Pydantic request/response schemas for Users API."""
from __future__ import annotations

from pydantic import BaseModel, EmailStr


class UserCreateIn(BaseModel):
    email: EmailStr
    name: str | None = None


class UserUpdateIn(BaseModel):
    name: str | None = None


class UserOut(BaseModel):
    id: str
    email: EmailStr
    name: str | None
