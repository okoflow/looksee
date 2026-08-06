"""Owner setup, login, and session-user lookup."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from api.adapters.persistence.models import User
from api.adapters.security import hash_password, verify_password
from api.application.errors import InvalidCredentialsError, ResourceConflictError

if TYPE_CHECKING:
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def requires_setup(session: AsyncSession) -> bool:
    """True until the first (owner) account exists."""
    user_count = await session.scalar(select(func.count(User.id)))

    return user_count == 0


async def create_owner(session: AsyncSession, *, email: str, name: str, password: str) -> User:
    if not await requires_setup(session):
        raise ResourceConflictError("the instance owner is already set up")

    owner = User(
        email=normalize_email(email),
        name=name,
        password_hash=hash_password(password),
        role="owner",
    )
    session.add(owner)
    await session.commit()
    await session.refresh(owner)

    return owner


async def authenticate(session: AsyncSession, *, email: str, password: str) -> User:
    result = await session.execute(select(User).where(User.email == normalize_email(email)))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentialsError("invalid email or password")

    return user


async def get_user(session: AsyncSession, user_id: UUID) -> User | None:
    return await session.get(User, user_id)
