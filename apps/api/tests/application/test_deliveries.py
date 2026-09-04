import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from api.application.deliveries import DeliveryJob, DeliveryRequest, DeliveryWorker, QueueingActions
from api.application.errors import DeliveryError, RetryableFrameError
from api.domain.workflow import LogAlertActionData, SnapshotActionData, WebhookActionData

NOW = datetime(2026, 9, 4, tzinfo=UTC)


@pytest.fixture
def delivery_request(identity, make_event):
    return DeliveryRequest(
        identity=identity,
        event=make_event(),
        action=WebhookActionData(url="https://example.com/events"),
        context={"snapshot_url": "/snapshots/evidence.jpg"},
    )


@pytest.fixture
def queue(delivery_request):
    job = DeliveryJob(uuid4(), uuid4(), 1, delivery_request)

    return SimpleNamespace(
        enqueue=AsyncMock(),
        reserve=AsyncMock(return_value=job),
        complete=AsyncMock(),
        fail=AsyncMock(),
    )


def test_persisted_request_round_trips_without_changing_deduplication(delivery_request):
    restored = DeliveryRequest.model_validate_json(delivery_request.model_dump_json())

    assert restored == delivery_request
    assert restored.deduplication_key() == delivery_request.deduplication_key()


async def test_successful_delivery_acknowledges_the_lease(queue):
    send = AsyncMock()
    worker = DeliveryWorker(queue, send, clock=lambda: NOW)

    assert await worker.run_once()

    send.assert_awaited_once_with(queue.reserve.return_value)
    queue.complete.assert_awaited_once_with(queue.reserve.return_value)
    queue.fail.assert_not_awaited()


@pytest.mark.parametrize("retryable", [True, False])
async def test_provider_failure_retries_only_when_recoverable(queue, retryable):
    worker = DeliveryWorker(
        queue,
        AsyncMock(side_effect=DeliveryError("provider unavailable", retryable=retryable)),
        clock=lambda: NOW,
    )

    await worker.run_once()

    queue.fail.assert_awaited_once_with(
        queue.reserve.return_value,
        "provider unavailable",
        NOW + timedelta(seconds=2) if retryable else None,
    )
    queue.complete.assert_not_awaited()


async def test_retry_budget_stops_an_endless_failure(queue):
    worker = DeliveryWorker(
        queue,
        AsyncMock(side_effect=DeliveryError("unavailable")),
        clock=lambda: NOW,
        max_attempts=1,
    )

    await worker.run_once()

    queue.fail.assert_awaited_once_with(queue.reserve.return_value, "unavailable", None)


async def test_unexpected_provider_error_does_not_leak_secrets(queue, caplog):
    worker = DeliveryWorker(
        queue,
        AsyncMock(side_effect=RuntimeError("https://secret-token@provider")),
        clock=lambda: NOW,
    )

    await worker.run_once()

    assert "secret-token" not in caplog.text
    assert queue.fail.await_args.args[1] == "delivery adapter failed"


async def test_shutdown_leaves_the_lease_recoverable(queue):
    worker = DeliveryWorker(queue, AsyncMock(side_effect=asyncio.CancelledError))

    with pytest.raises(asyncio.CancelledError):
        await worker.run_once()

    queue.complete.assert_not_awaited()
    queue.fail.assert_not_awaited()


async def test_idle_worker_does_not_send(queue):
    queue.reserve.return_value = None
    send = AsyncMock()

    assert not await DeliveryWorker(queue, send).run_once()
    send.assert_not_awaited()


async def test_external_action_is_persisted_without_binary_snapshot(queue, delivery_request):
    local = AsyncMock()
    runner = QueueingActions(queue, local)
    request = delivery_request

    await runner(
        request.identity,
        request.event,
        request.action,
        {**request.context, "snapshot_jpeg": b"jpeg"},
    )

    queued = queue.enqueue.await_args.args[0]
    assert queued.context == request.context
    local.assert_not_awaited()


@pytest.mark.parametrize("action", [LogAlertActionData(), SnapshotActionData()])
async def test_local_actions_run_before_their_downstream_delivery(queue, delivery_request, action):
    local = AsyncMock()
    runner = QueueingActions(queue, local)

    await runner(delivery_request.identity, delivery_request.event, action, {})

    local.assert_awaited_once()
    queue.enqueue.assert_not_awaited()


async def test_unavailable_queue_keeps_frame_retryable(queue, delivery_request):
    queue.enqueue.side_effect = RuntimeError("database disconnected")
    runner = QueueingActions(queue, AsyncMock())

    with pytest.raises(RetryableFrameError):
        await runner(delivery_request.identity, delivery_request.event, delivery_request.action, {})
