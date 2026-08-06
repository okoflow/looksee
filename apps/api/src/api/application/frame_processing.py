"""Handle one accepted detection frame: load context, derive events, run the graph."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from sqlalchemy import select

from api.adapters.actions.dispatcher import dispatch_action
from api.adapters.filesystem.model_catalog import model_catalog
from api.adapters.persistence.db import session_factory
from api.adapters.persistence.models import Camera, Workflow
from api.adapters.realtime.broadcaster import broadcaster
from api.adapters.redis.commands import publish_stream_command
from api.adapters.state.memory import runtime_state
from api.application.camera_runtime import matches_desired_run, parse_start_command
from api.application.events import derive_events
from api.application.execution import ActionRunner, ExecutionIdentity, execute_event
from api.config import settings
from api.domain.errors import WorkflowGraphError
from api.domain.graph import WorkflowGraphIndex
from api.domain.workflow import RuntimeState, WorkflowGraph
from shared import DetectionFrame, StartStream, StopStream, StreamCommand

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from uuid import UUID
    from zoneinfo import ZoneInfo

    from api.application.workflow_validation import ModelCatalogReader
    from api.domain.models import ModelDescriptor
    from shared import EventKind

logger = logging.getLogger(__name__)

type CommandPublisher = Callable[[StreamCommand], Awaitable[None]]
type RealtimePublisher = Callable[[UUID, dict[str, Any]], Awaitable[None]]


class FrameRuntimeState(RuntimeState, Protocol):
    def event_cooldown_ready(
        self,
        camera_id: UUID,
        run_id: UUID,
        kind: EventKind,
        seconds: float,
    ) -> bool: ...

    def touch_event_cooldown(self, camera_id: UUID, run_id: UUID, kind: EventKind) -> None: ...


@dataclass(frozen=True, slots=True)
class FrameProcessingDependencies:
    """Effects and configuration one frame needs, mirroring inference's WorkerDependencies."""

    catalog: ModelCatalogReader
    publish_command: CommandPublisher
    runtime_state: FrameRuntimeState
    event_cooldown_seconds: float
    event_timezone: ZoneInfo
    publish_realtime: RealtimePublisher
    run_action: ActionRunner


_dependencies = FrameProcessingDependencies(
    catalog=model_catalog,
    publish_command=publish_stream_command,
    runtime_state=runtime_state,
    event_cooldown_seconds=settings.event_cooldown_seconds,
    event_timezone=settings.event_timezone,
    publish_realtime=broadcaster.publish,
    run_action=dispatch_action,
)


@dataclass(frozen=True, slots=True)
class _FrameContext:
    desired: StartStream
    index: WorkflowGraphIndex
    source_node_id: str
    identity: ExecutionIdentity


async def handle_detection_frame(frame: DetectionFrame) -> None:
    context, should_stop = await _load_frame_context(frame)
    if should_stop:
        await _stop_frame_run(frame, _dependencies.publish_command)
        return
    if context is None:
        return

    model = await asyncio.to_thread(_dependencies.catalog.get, context.desired.config.model_id)
    if model is None:
        logger.warning("dropping frame for unavailable model=%s", context.desired.config.model_id)
        return

    try:
        await process_frame(
            frame,
            model,
            context.index,
            context.source_node_id,
            context.identity,
            _dependencies,
        )
    except Exception:
        logger.exception("frame processing failed camera=%s", frame.camera_id)


async def process_frame(
    frame: DetectionFrame,
    model: ModelDescriptor,
    index: WorkflowGraphIndex,
    source_node_id: str,
    identity: ExecutionIdentity,
    dependencies: FrameProcessingDependencies,
) -> None:
    await dependencies.publish_realtime(
        frame.camera_id,
        {
            "type": "detections",
            "ts": frame.timestamp.isoformat(),
            "frame_width": frame.frame_width,
            "frame_height": frame.frame_height,
            "detections": [detection.model_dump(mode="json") for detection in frame.detections],
        },
    )

    for event in derive_events(frame, model):
        if not dependencies.runtime_state.event_cooldown_ready(
            event.camera_id,
            identity.run_id,
            event.kind,
            dependencies.event_cooldown_seconds,
        ):
            continue

        await dependencies.publish_realtime(
            event.camera_id,
            {
                "type": "event",
                "kind": event.kind,
                "ts": event.ts.isoformat(),
                "frame_width": event.frame_width,
                "frame_height": event.frame_height,
                "detections": [detection.model_dump(mode="json") for detection in event.detections],
            },
        )
        await execute_event(
            index,
            source_node_id,
            identity,
            event,
            dependencies.event_timezone,
            dependencies.runtime_state,
            dependencies.run_action,
        )

        dependencies.runtime_state.touch_event_cooldown(
            event.camera_id,
            identity.run_id,
            event.kind,
        )


async def _load_frame_context(frame: DetectionFrame) -> tuple[_FrameContext | None, bool]:
    try:
        async with session_factory() as session:
            result = await session.execute(
                select(
                    Camera.workflow_id,
                    Camera.node_id,
                    Camera.name,
                    Camera.start_command,
                    Workflow.enabled,
                    Workflow.graph,
                )
                .join(Workflow, Workflow.id == Camera.workflow_id)
                .where(Camera.id == frame.camera_id)
            )
            row = result.one_or_none()
    except Exception:
        logger.exception("camera/workflow lookup failed camera=%s", frame.camera_id)

        return None, False

    if row is None:
        return None, True
    if row.workflow_id != frame.workflow_id:
        return None, True
    if row.start_command is None:
        return None, True

    desired = parse_start_command(frame.camera_id, row.start_command)
    if desired is None:
        return None, False

    try:
        if not matches_desired_run(frame, desired):
            logger.debug(
                "dropping stale frame camera=%s frame_revision=%s desired_revision=%s "
                "frame_run=%s desired_run=%s",
                frame.camera_id,
                frame.revision,
                desired.revision,
                frame.run_id,
                desired.run_id,
            )

            return None, False

        if not row.enabled:
            return None, False

        graph = WorkflowGraph.model_validate(row.graph)

        return (
            _FrameContext(
                desired=desired,
                index=WorkflowGraphIndex.build(graph),
                source_node_id=row.node_id,
                identity=ExecutionIdentity(
                    workflow_id=row.workflow_id,
                    run_id=frame.run_id,
                    camera_name=row.name,
                ),
            ),
            False,
        )
    except (ValueError, WorkflowGraphError):
        logger.exception("invalid persisted runtime state camera=%s", frame.camera_id)

        return None, False


async def _stop_frame_run(frame: DetectionFrame, publish_command: CommandPublisher) -> None:
    logger.debug("stopping frame run for unknown or disabled camera %s", frame.camera_id)
    await publish_command(
        StopStream(
            camera_id=frame.camera_id,
            revision=frame.revision,
            run_id=frame.run_id,
        )
    )
