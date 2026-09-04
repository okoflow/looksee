"""Account use cases and their infrastructure ports."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Protocol

from api.application.errors import InvalidCredentialsError

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID


class Account(Protocol):
    id: UUID
    email: str
    name: str
    password_hash: str
    role: str
    created_at: datetime


class AccountRepository(Protocol):
    async def any_users(self) -> bool: ...

    async def claim_owner(self, *, email: str, name: str, password_hash: str) -> Account: ...

    async def by_email(self, email: str) -> Account | None: ...

    async def by_id(self, user_id: UUID) -> Account | None: ...


class Passwords(Protocol):
    def hash(self, password: str) -> str: ...

    def verify(self, password: str, password_hash: str | None) -> bool: ...


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def requires_setup(accounts: AccountRepository) -> bool:
    return not await accounts.any_users()


async def create_owner(
    accounts: AccountRepository,
    passwords: Passwords,
    *,
    email: str,
    name: str,
    password: str,
) -> Account:
    hashed = await asyncio.to_thread(passwords.hash, password)

    return await accounts.claim_owner(email=normalize_email(email), name=name, password_hash=hashed)


async def authenticate(
    accounts: AccountRepository,
    passwords: Passwords,
    *,
    email: str,
    password: str,
) -> Account:
    user = await accounts.by_email(normalize_email(email))
    valid = await asyncio.to_thread(
        passwords.verify, password, user.password_hash if user is not None else None
    )
    if user is None or not valid:
        raise InvalidCredentialsError("invalid email or password")

    return user


async def get_user(accounts: AccountRepository, user_id: UUID) -> Account | None:
    return await accounts.by_id(user_id)
