"""Accept inference worker lifecycle events and project them onto camera status."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from sqlalchemy import select

from api.adapters.persistence.models import Camera
from api.adapters.realtime.broadcaster import broadcaster
from api.adapters.redis.commands import publish_stream_command
from api.adapters.state.memory import runtime_state
from api.application.camera_runtime import matches_desired_run, parse_start_command
from api.domain.enums import CameraStatus
from shared import StartStream, StopStream, WorkerErrored, WorkerStarted, WorkerStopped

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from shared import WorkerEvent

logger = logging.getLogger(__name__)

_STATUS_BY_EVENT_TYPE: dict[str, CameraStatus] = {
    "worker_started": CameraStatus.ACTIVE,
    "worker_stopped": CameraStatus.DISABLED,
    "worker_errored": CameraStatus.ERROR,
}


@dataclass(frozen=True, slots=True)
class WorkerTarget:
    runtime_revision: int
    desired_start: StartStream | None


@dataclass(frozen=True, slots=True)
class WorkerStatusDecision:
    status: CameraStatus | None = None
    reason: str | None = None
    stop_command: StopStream | None = None


def decide_worker_event(
    target: WorkerTarget | None,
    event: WorkerEvent,
) -> WorkerStatusDecision:
    if target is None:
        return WorkerStatusDecision(stop_command=_orphan_stop(event))

    desired = target.desired_start
    if desired is None:
        if event.revision != target.runtime_revision:
            return WorkerStatusDecision(stop_command=_orphan_stop(event))
        if not isinstance(event, WorkerStopped):
            return WorkerStatusDecision(stop_command=_orphan_stop(event))

        return WorkerStatusDecision(status=CameraStatus.DISABLED)

    if not matches_desired_run(event, desired):
        return WorkerStatusDecision()

    reason = event.reason if isinstance(event, WorkerErrored) else None

    return WorkerStatusDecision(status=_STATUS_BY_EVENT_TYPE[event.type], reason=reason)


def _orphan_stop(event: WorkerEvent) -> StopStream | None:
    """Only a started worker occupies a camera and needs an explicit cancellation."""
    if not isinstance(event, WorkerStarted):
        return None

    return StopStream(camera_id=event.camera_id, revision=event.revision, run_id=event.run_id)


async def apply_worker_event(
    session: AsyncSession,
    event: WorkerEvent,
) -> None:
    result = await session.execute(
        select(Camera).where(Camera.id == event.camera_id).with_for_update()
    )
    camera = result.scalar_one_or_none()

    desired_start: StartStream | None = None
    if camera is not None and camera.start_command is not None:
        desired_start = parse_start_command(camera.id, camera.start_command)
        if desired_start is None:
            return

    target: WorkerTarget | None = None
    if camera is not None:
        target = WorkerTarget(
            runtime_revision=camera.runtime_revision,
            desired_start=desired_start,
        )

    decision = decide_worker_event(target, event)

    if decision.status in (CameraStatus.ACTIVE, CameraStatus.DISABLED):
        runtime_state.clear_worker_retry(event.camera_id)

    status_changed = (
        camera is not None and decision.status is not None and camera.status != decision.status
    )
    if status_changed:
        camera.status = decision.status
        await session.commit()
    else:
        await session.rollback()

    if decision.stop_command is not None:
        logger.info("stopping orphan worker camera=%s", event.camera_id)
        await publish_stream_command(decision.stop_command)

    if camera is None or decision.status is None:
        return

    if decision.reason is not None:
        logger.warning("worker errored camera=%s reason=%s", event.camera_id, decision.reason)

    await broadcaster.publish(
        event.camera_id,
        {
            "type": "worker",
            "status": decision.status.value,
            "ts": event.timestamp.isoformat(),
            "reason": decision.reason,
        },
    )
