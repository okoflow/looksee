from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.adapters.persistence.models import User
from api.application.errors import ResourceConflictError

_OWNER_SETUP_LOCK = 4_672_793_681


class SqlAlchemyAccounts:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def any_users(self) -> bool:
        return bool(await self._session.scalar(select(func.count(User.id))))

    async def claim_owner(self, *, email: str, name: str, password_hash: str) -> User:
        await self._session.execute(select(func.pg_advisory_xact_lock(_OWNER_SETUP_LOCK)))
        if await self.any_users():
            await self._session.rollback()
            raise ResourceConflictError("the instance owner is already set up")

        owner = User(email=email, name=name, password_hash=password_hash, role="owner")
        self._session.add(owner)
        await self._session.commit()
        await self._session.refresh(owner)

        return owner

    async def by_email(self, email: str) -> User | None:
        result = await self._session.execute(select(User).where(User.email == email))

        return result.scalar_one_or_none()

    async def by_id(self, user_id: UUID) -> User | None:
        return await self._session.get(User, user_id)
