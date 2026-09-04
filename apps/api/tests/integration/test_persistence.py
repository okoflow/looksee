import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, select

from api.adapters.persistence.accounts import SqlAlchemyAccounts
from api.adapters.persistence.deliveries import PostgresDeliveryQueue
from api.adapters.persistence.models import Delivery, User
from api.adapters.redis.rate_limits import RedisRateLimiter
from api.application.deliveries import DeliveryRequest
from api.application.errors import ResourceConflictError
from api.domain.workflow import WebhookActionData


async def test_concurrent_setup_creates_exactly_one_owner(postgres_sessions):
    async def claim(email):
        async with postgres_sessions() as session:
            return await SqlAlchemyAccounts(session).claim_owner(
                email=email,
                name="Owner",
                password_hash="already-hashed",
            )

    results = await asyncio.gather(
        *(claim(f"owner-{index}@example.com") for index in range(8)),
        return_exceptions=True,
    )

    assert sum(isinstance(result, User) for result in results) == 1
    assert sum(isinstance(result, ResourceConflictError) for result in results) == 7
    async with postgres_sessions() as session:
        assert await session.scalar(select(func.count()).select_from(User)) == 1


async def test_queue_deduplicates_concurrent_enqueues_and_claims(
    postgres_sessions, identity, make_event
):
    queue = PostgresDeliveryQueue(postgres_sessions)
    request = DeliveryRequest(
        identity=identity,
        event=make_event(),
        action=WebhookActionData(url="https://example.com"),
        context={},
    )

    await asyncio.gather(*(queue.enqueue(request) for _ in range(8)))
    jobs = await asyncio.gather(*(queue.reserve(datetime.now(UTC)) for _ in range(8)))

    assert len([job for job in jobs if job is not None]) == 1
    async with postgres_sessions() as session:
        assert await session.scalar(select(func.count()).select_from(Delivery)) == 1


async def test_expired_lease_is_recovered_and_old_worker_cannot_ack(
    postgres_sessions, identity, make_event
):
    queue = PostgresDeliveryQueue(postgres_sessions)
    await queue.enqueue(
        DeliveryRequest(
            identity=identity,
            event=make_event(),
            action=WebhookActionData(url="https://example.com"),
            context={},
        )
    )
    now = datetime.now(UTC)
    abandoned = await queue.reserve(now)
    restarted = PostgresDeliveryQueue(postgres_sessions)

    assert await restarted.reserve(now + timedelta(seconds=59)) is None
    recovered = await restarted.reserve(now + timedelta(seconds=61))
    assert recovered.id == abandoned.id
    assert recovered.attempts == 2
    assert recovered.lease_id != abandoned.lease_id

    await queue.complete(abandoned)
    async with postgres_sessions() as session:
        assert (await session.get(Delivery, recovered.id)).status == "processing"

    await restarted.complete(recovered)
    async with postgres_sessions() as session:
        row = await session.get(Delivery, recovered.id)
        assert row.status == "sent"
        assert row.payload == {}


async def test_failed_delivery_waits_until_its_retry_time(postgres_sessions, identity, make_event):
    queue = PostgresDeliveryQueue(postgres_sessions)
    await queue.enqueue(
        DeliveryRequest(
            identity=identity,
            event=make_event(),
            action=WebhookActionData(url="https://example.com"),
            context={},
        )
    )
    now = datetime.now(UTC)
    job = await queue.reserve(now)

    await queue.fail(job, "provider unavailable", now + timedelta(seconds=10))

    assert await queue.reserve(now + timedelta(seconds=9)) is None
    retried = await queue.reserve(now + timedelta(seconds=10))
    assert retried.id == job.id
    assert retried.attempts == 2

    await queue.fail(retried, "rejected", None)

    assert await queue.reserve(now + timedelta(days=1)) is None

    [failed] = await queue.recent("failed", 100)
    assert failed.id == job.id
    assert failed.last_error == "rejected"
    assert "payload" not in failed.model_dump()

    assert await queue.retry(job.id)
    assert not await queue.retry(job.id)
    resumed = await queue.reserve(datetime.now(UTC))
    assert resumed.attempts == 1


async def test_rate_limiter_is_atomic_and_sets_expiry(valkey):
    key = f"integration:{uuid4().hex}"
    limiter = RedisRateLimiter(valkey)
    try:
        results = await asyncio.gather(
            *(limiter.allow(key, limit=5, window_seconds=60) for _ in range(20)),
        )

        assert sum(results) == 5
        assert 0 < await valkey.ttl(f"looksee:rate:{key}") <= 60
    finally:
        await valkey.delete(f"looksee:rate:{key}")
