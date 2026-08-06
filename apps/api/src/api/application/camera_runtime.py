"""Project workflow sources into camera desired state and runtime side effects."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy import select

from api.adapters.mediamtx.client import delete_camera_path, upsert_camera_path
from api.adapters.persistence.db import session_factory
from api.adapters.persistence.models import Camera, Workflow
from api.adapters.redis.commands import publish_stream_command
from api.application.assets import ensure_cached
from api.domain.enums import CameraSource, CameraStatus
from shared import StartStream, StopStream, StreamCommand, WorkflowConfig

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from api.domain.graph import WorkflowGraphIndex
    from api.domain.workflow import CameraSourceData

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class CameraRuntimePlan:
    """Post-commit MediaMTX and inference effects calculated in a transaction."""

    upsert_path_ids: set[UUID] = field(default_factory=set)
    delete_path_ids: list[UUID] = field(default_factory=list)
    commands: list[StreamCommand] = field(default_factory=list)
    restart_camera_ids: set[UUID] = field(default_factory=set)


class DesiredRunReport(Protocol):
    """Identity fields every detection frame and worker event carries for run fencing."""

    workflow_id: UUID
    revision: int
    run_id: UUID
    model_id: str


def matches_desired_run(report: DesiredRunReport, desired: StartStream) -> bool:
    if report.workflow_id != desired.workflow_id:
        return False
    if report.revision != desired.revision:
        return False
    if report.run_id != desired.run_id:
        return False

    return report.model_id == desired.config.model_id


def inference_config(index: WorkflowGraphIndex, source_node_id: str) -> WorkflowConfig:
    selected = index.selected_detect_for_source(source_node_id)

    return WorkflowConfig(
        model_id=selected.model_id,
        confidence_threshold=selected.data.confidence_threshold,
        inference_fps=selected.data.inference_fps,
    )


def start_is_current(
    current: StartStream | None,
    *,
    workflow_id: UUID,
    runtime_revision: int,
    config: WorkflowConfig,
    force_restart: bool,
) -> bool:
    if current is None:
        return False
    if force_restart:
        return False
    if current.revision != runtime_revision:
        return False
    if current.workflow_id != workflow_id:
        return False

    return current.config == config


def parse_start_command(camera_id: UUID, raw: dict[str, Any] | None) -> StartStream | None:
    """Parse a camera's persisted desired-run command; None when absent or invalid."""
    if raw is None:
        return None

    try:
        return StartStream.model_validate(raw)
    except ValueError as exc:
        logger.warning("invalid persisted start command camera=%s reason=%s", camera_id, exc)

        return None


def _next_runtime_revision(camera: Camera) -> int:
    camera.runtime_revision += 1

    return camera.runtime_revision


def _persisted_source_url(data: CameraSourceData) -> str | None:
    """WebRTC is publisher-mode and a blank draft URL means "not configured yet"."""
    if data.source_type == CameraSource.WEBRTC:
        return None
    if not data.url:
        return None

    return data.url


def _stop_command(camera: Camera) -> StopStream:
    command = parse_start_command(camera.id, camera.start_command)

    return StopStream(
        camera_id=camera.id,
        revision=_next_runtime_revision(camera),
        run_id=command.run_id if command is not None else None,
    )


async def _locked_workflow_cameras(
    session: AsyncSession,
    workflow_id: UUID,
) -> list[Camera]:
    result = await session.execute(
        select(Camera).where(Camera.workflow_id == workflow_id).with_for_update()
    )

    return list(result.scalars().all())


async def sync_workflow_cameras(
    session: AsyncSession,
    workflow: Workflow,
    index: WorkflowGraphIndex,
    plan: CameraRuntimePlan | None = None,
) -> CameraRuntimePlan:
    """Mutate camera rows to match source nodes without performing external side effects."""
    if plan is None:
        plan = CameraRuntimePlan()

    sources = index.source_nodes()
    existing = {
        camera.node_id: camera for camera in await _locked_workflow_cameras(session, workflow.id)
    }

    for node_id, camera in existing.items():
        if node_id in sources:
            continue

        plan.commands.append(_stop_command(camera))
        plan.delete_path_ids.append(camera.id)
        await session.delete(camera)

    for node_id, data in sources.items():
        source_url = _persisted_source_url(data)
        camera = existing.get(node_id)

        if camera is None:
            camera = Camera(
                workflow_id=workflow.id,
                node_id=node_id,
                name=data.name,
                source_type=data.source_type,
                source_url=source_url,
            )
            session.add(camera)
            await session.flush()
            plan.upsert_path_ids.add(camera.id)
            continue

        source_changed = camera.source_type != data.source_type or camera.source_url != source_url

        camera.name = data.name
        camera.source_type = data.source_type
        camera.source_url = source_url

        if source_changed:
            plan.upsert_path_ids.add(camera.id)
            plan.restart_camera_ids.add(camera.id)

    return plan


async def start_workflow_cameras(
    session: AsyncSession,
    workflow: Workflow,
    index: WorkflowGraphIndex,
    plan: CameraRuntimePlan | None = None,
) -> CameraRuntimePlan:
    """Persist changed desired runs; unchanged inference configs remain untouched."""
    if plan is None:
        plan = CameraRuntimePlan()

    for camera in await _locked_workflow_cameras(session, workflow.id):
        config = inference_config(index, camera.node_id)
        current = parse_start_command(camera.id, camera.start_command)
        unchanged = start_is_current(
            current,
            workflow_id=workflow.id,
            runtime_revision=camera.runtime_revision,
            config=config,
            force_restart=camera.id in plan.restart_camera_ids,
        )
        if unchanged:
            continue

        command = StartStream(
            camera_id=camera.id,
            workflow_id=workflow.id,
            revision=_next_runtime_revision(camera),
            run_id=uuid4(),
            config=config,
        )
        camera.start_command = command.model_dump(mode="json")
        camera.status = CameraStatus.PENDING
        plan.commands.append(command)

    return plan


async def stop_workflow_cameras(
    session: AsyncSession,
    workflow: Workflow,
    plan: CameraRuntimePlan | None = None,
) -> CameraRuntimePlan:
    """Persist disabled desired state and prepare targeted cancellation commands."""
    if plan is None:
        plan = CameraRuntimePlan()

    for camera in await _locked_workflow_cameras(session, workflow.id):
        plan.commands.append(_stop_command(camera))
        camera.start_command = None
        camera.status = CameraStatus.DISABLED

    return plan


async def teardown_workflow_cameras(
    session: AsyncSession,
    workflow: Workflow,
    plan: CameraRuntimePlan | None = None,
) -> CameraRuntimePlan:
    """Prepare cleanup before deleting a workflow and its camera rows."""
    if plan is None:
        plan = CameraRuntimePlan()

    for camera in await _locked_workflow_cameras(session, workflow.id):
        plan.commands.append(_stop_command(camera))
        plan.delete_path_ids.append(camera.id)

    return plan


async def _upsert_desired_camera_path(camera_id: UUID) -> None:
    """Apply the latest committed path without holding a DB connection during HTTP I/O."""
    async with session_factory() as session:
        result = await session.execute(
            select(Camera.id, Camera.source_type, Camera.source_url).where(Camera.id == camera_id)
        )
        camera = result.one_or_none()

    if camera is None:
        await delete_camera_path(camera_id)
        return

    try:
        source_url = camera.source_url
        if camera.source_type == CameraSource.FILE and source_url is not None:
            source_url = await ensure_cached(source_url)

        await upsert_camera_path(camera.id, camera.source_type, source_url)
    except Exception:
        logger.exception("mediamtx provisioning failed camera=%s; reconcile will retry", camera.id)


async def apply_camera_runtime_plan(plan: CameraRuntimePlan) -> None:
    """Apply idempotent external effects after their desired state is committed."""
    for camera_id in sorted(plan.upsert_path_ids, key=str):
        await _upsert_desired_camera_path(camera_id)

    for command in plan.commands:
        try:
            await publish_stream_command(command)
        except Exception:
            logger.exception(
                "stream command publish failed camera=%s type=%s",
                command.camera_id,
                command.type,
            )

    for camera_id in plan.delete_path_ids:
        await delete_camera_path(camera_id)
