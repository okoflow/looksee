"""Durable delivery orchestration through replaceable queue and sender ports."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, Literal, Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from api.application.errors import DeliveryError, RetryableFrameError
from api.application.execution import ActionRunner, ExecutionIdentity
from api.domain.events import DetectionEvent
from api.domain.workflow import ActionNodeData, LogAlertActionData, SnapshotActionData
from api.domain.workflow.nodes import NodeData

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)


class DeliveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    identity: ExecutionIdentity
    event: DetectionEvent
    action: NodeData
    context: dict[str, Any]

    @field_validator("action")
    @classmethod
    def external_action(cls, value: NodeData) -> ActionNodeData:
        if not isinstance(value, ActionNodeData) or isinstance(
            value, LogAlertActionData | SnapshotActionData
        ):
            raise ValueError("expected an external delivery action")

        return value

    def deduplication_key(self) -> str:
        identity = self.identity
        event = self.event
        parts = (
            str(identity.workflow_id),
            str(event.camera_id),
            str(identity.run_id),
            identity.node_id,
            event.kind,
            event.ts.isoformat(),
        )

        return hashlib.sha256("\n".join(parts).encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class DeliveryJob:
    id: UUID
    lease_id: UUID
    attempts: int
    request: DeliveryRequest


class DeliveryQueue(Protocol):
    async def enqueue(self, request: DeliveryRequest) -> None: ...

    async def reserve(self, now: datetime) -> DeliveryJob | None: ...

    async def complete(self, job: DeliveryJob) -> None: ...

    async def fail(self, job: DeliveryJob, reason: str, retry_at: datetime | None) -> None: ...


type DeliveryStatus = Literal["pending", "processing", "sent", "failed"]


class DeliveryRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: DeliveryStatus
    attempts: int
    available_at: datetime
    last_error: str | None
    created_at: datetime


class DeliveryHistory(Protocol):
    async def recent(self, status: DeliveryStatus | None, limit: int) -> list[DeliveryRecord]: ...

    async def retry(self, delivery_id: UUID) -> bool: ...


class QueueingActions:
    def __init__(self, queue: DeliveryQueue, local_actions: ActionRunner) -> None:
        self._queue = queue
        self._local_actions = local_actions

    async def __call__(
        self,
        identity: ExecutionIdentity,
        event: DetectionEvent,
        action: ActionNodeData,
        context: dict[str, Any],
    ) -> None:
        if isinstance(action, LogAlertActionData | SnapshotActionData):
            await self._local_actions(identity, event, action, context)
            return

        request = DeliveryRequest(
            identity=identity,
            event=event,
            action=action,
            context={key: value for key, value in context.items() if key != "snapshot_jpeg"},
        )
        try:
            await self._queue.enqueue(request)
        except Exception:
            raise RetryableFrameError("delivery could not be persisted") from None


class DeliveryWorker:
    def __init__(
        self,
        queue: DeliveryQueue,
        send: Callable[[DeliveryJob], Awaitable[None]],
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        max_attempts: int = 8,
        timeout_seconds: float = 30,
    ) -> None:
        self._queue = queue
        self._send = send
        self._clock = clock
        self._max_attempts = max_attempts
        self._timeout_seconds = timeout_seconds

    async def run_once(self) -> bool:
        job = await self._queue.reserve(self._clock())
        if job is None:
            return False

        try:
            async with asyncio.timeout(self._timeout_seconds):
                await self._send(job)
        except DeliveryError as exc:
            await self._record_failure(job, str(exc), exc.retryable)
        except TimeoutError:
            await self._record_failure(job, "delivery timed out", True)
        except Exception:
            await self._record_failure(job, "delivery adapter failed", True)
        else:
            await self._queue.complete(job)

        return True

    async def run(self) -> None:
        while True:
            try:
                worked = await self.run_once()
            except Exception:
                logger.warning("delivery queue unavailable")
                worked = False

            if not worked:
                await asyncio.sleep(1)

    async def _record_failure(self, job: DeliveryJob, reason: str, retryable: bool) -> None:
        retry_at = None
        if retryable and job.attempts < self._max_attempts:
            delay = min(300, 2 ** min(job.attempts, 9))
            retry_at = self._clock() + timedelta(seconds=delay)

        await self._queue.fail(job, reason, retry_at)
        logger.warning("delivery failed id=%s retry=%s reason=%s", job.id, retry_at, reason)
