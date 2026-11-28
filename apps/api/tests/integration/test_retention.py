from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, update

from api.adapters.persistence.models import Alert, Delivery
from api.adapters.persistence.retention import SqlAlchemyRetention


async def _age(sessions, model, row_id, *, days):
    async with sessions() as session:
        stamp = datetime.now(UTC) - timedelta(days=days)
        await session.execute(
            update(model).where(model.id == row_id).values(created_at=stamp, updated_at=stamp)
        )
        await session.commit()


async def _count(sessions, model):
    async with sessions() as session:
        return await session.scalar(select(func.count()).select_from(model))


async def test_alerts_older_than_the_cutoff_are_deleted(postgres_sessions):
    async with postgres_sessions() as session:
        old = Alert(kind="enter", message="old")
        fresh = Alert(kind="enter", message="fresh")
        session.add_all([old, fresh])
        await session.commit()
        old_id = old.id
    await _age(postgres_sessions, Alert, old_id, days=40)

    removed = await SqlAlchemyRetention(postgres_sessions).purge_alerts(
        datetime.now(UTC) - timedelta(days=30)
    )

    assert removed == 1
    assert await _count(postgres_sessions, Alert) == 1


async def test_only_finished_deliveries_expire(postgres_sessions):
    now = datetime.now(UTC)
    rows = {
        status: Delivery(deduplication_key=status, payload={}, status=status, available_at=now)
        for status in ("pending", "processing", "sent", "failed")
    }
    async with postgres_sessions() as session:
        session.add_all(rows.values())
        await session.commit()
        ids = [row.id for row in rows.values()]
    for row_id in ids:
        await _age(postgres_sessions, Delivery, row_id, days=40)

    removed = await SqlAlchemyRetention(postgres_sessions).purge_deliveries(
        now - timedelta(days=30)
    )

    assert removed == 2
    async with postgres_sessions() as session:
        left = set(await session.scalars(select(Delivery.status)))
    assert left == {"pending", "processing"}
