from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert

from api.adapters.persistence.models import Delivery
from api.application.deliveries import DeliveryJob, DeliveryRecord, DeliveryRequest, DeliveryStatus

if TYPE_CHECKING:
    from collections.abc import Callable
    from uuid import UUID

    from sqlalchemy.ext.asyncio import AsyncSession


class PostgresDeliveryQueue:
    def __init__(self, sessions: Callable[[], AsyncSession]) -> None:
        self._sessions = sessions

    async def enqueue(self, request: DeliveryRequest) -> None:
        statement = (
            insert(Delivery)
            .values(
                deduplication_key=request.deduplication_key(),
                payload=request.model_dump(mode="json"),
                available_at=datetime.now(UTC),
            )
            .on_conflict_do_nothing(index_elements=[Delivery.deduplication_key])
        )
        async with self._sessions() as session:
            await session.execute(statement)
            await session.commit()

    async def reserve(self, now: datetime) -> DeliveryJob | None:
        statement = (
            select(Delivery)
            .where(
                or_(
                    and_(Delivery.status == "pending", Delivery.available_at <= now),
                    and_(Delivery.status == "processing", Delivery.lease_until <= now),
                )
            )
            .order_by(Delivery.available_at, Delivery.id)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        async with self._sessions() as session:
            row = (await session.execute(statement)).scalar_one_or_none()
            if row is None:
                return None

            try:
                request = DeliveryRequest.model_validate(row.payload)
            except ValueError:
                row.status = "failed"
                row.last_error = "invalid persisted delivery"
                await session.commit()
                return None

            row.status = "processing"
            row.attempts += 1
            row.lease_id = uuid4()
            row.lease_until = now + timedelta(seconds=60)
            job = DeliveryJob(row.id, row.lease_id, row.attempts, request)
            await session.commit()

            return job

    async def complete(self, job: DeliveryJob) -> None:
        await self._finish(job, status="sent", payload={}, last_error=None)

    async def fail(self, job: DeliveryJob, reason: str, retry_at: datetime | None) -> None:
        fields = {"status": "failed", "last_error": reason[:256]}
        if retry_at is not None:
            fields.update(status="pending", available_at=retry_at)

        await self._finish(job, **fields)

    async def _finish(self, job: DeliveryJob, **fields: object) -> None:
        statement = (
            update(Delivery)
            .where(Delivery.id == job.id, Delivery.lease_id == job.lease_id)
            .values(**fields, lease_id=None, lease_until=None)
        )
        async with self._sessions() as session:
            await session.execute(statement)
            await session.commit()

    async def recent(self, status: DeliveryStatus | None, limit: int) -> list[DeliveryRecord]:
        statement = (
            select(Delivery).order_by(Delivery.created_at.desc(), Delivery.id.desc()).limit(limit)
        )
        if status is not None:
            statement = statement.where(Delivery.status == status)

        async with self._sessions() as session:
            rows = (await session.execute(statement)).scalars()

            return [DeliveryRecord.model_validate(row) for row in rows]

    async def retry(self, delivery_id: UUID) -> bool:
        statement = (
            update(Delivery)
            .where(Delivery.id == delivery_id, Delivery.status == "failed")
            .values(status="pending", attempts=0, available_at=datetime.now(UTC), last_error=None)
            .returning(Delivery.id)
        )
        async with self._sessions() as session:
            found = (await session.execute(statement)).scalar_one_or_none()
            await session.commit()

            return found is not None
