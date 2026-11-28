"""Delete persisted alerts and finished deliveries past their retention."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import delete

from api.adapters.persistence.models import Alert, Delivery

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy import CursorResult
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

_FINISHED_DELIVERY_STATUSES = ("sent", "failed")


class SqlAlchemyRetention:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def purge_alerts(self, cutoff: datetime) -> int:
        async with self._session_factory() as session:
            statement = delete(Alert).where(Alert.created_at < cutoff)
            result = await session.execute(statement)
            await session.commit()

        return _deleted(result)

    async def purge_deliveries(self, cutoff: datetime) -> int:
        """Remove sent and permanently failed deliveries; pending work is never touched."""
        async with self._session_factory() as session:
            result = await session.execute(
                delete(Delivery).where(
                    Delivery.status.in_(_FINISHED_DELIVERY_STATUSES),
                    Delivery.updated_at < cutoff,
                )
            )
            await session.commit()

        return _deleted(result)


def _deleted(result: object) -> int:
    # A DML statement always returns a CursorResult; the session API types it as Result.
    return cast("CursorResult[Any]", result).rowcount or 0
