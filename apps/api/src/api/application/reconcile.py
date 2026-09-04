"""Reconcile persisted camera desired state with MediaMTX and inference."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import httpx
from sqlalchemy import select

from api.adapters.mediamtx.client import delete_camera_path, list_path_names
from api.adapters.persistence.db import session_factory
from api.adapters.persistence.models import Camera
from api.adapters.redis.commands import publish_stream_command
from api.adapters.state.memory import runtime_state
from api.application.camera_runtime import (
    CameraRuntimePlan,
    apply_camera_runtime_plan,
    parse_start_command,
)
from api.config import settings
from api.domain.enums import CameraStatus
from shared import StopStream, StreamCommand, camera_id_from_path_name, camera_path_name

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Collection, Sequence
    from uuid import UUID

logger = logging.getLogger(__name__)

_MAX_RETRY_BACKOFF_SECONDS = 300.0


@dataclass(frozen=True, slots=True)
class CameraPathPlan:
    missing_ids: frozenset[UUID]
    orphan_ids: tuple[UUID, ...]


def plan_camera_paths(camera_ids: Collection[UUID], existing_names: set[str]) -> CameraPathPlan:
    desired_names = {camera_path_name(camera_id) for camera_id in camera_ids}
    missing_ids = frozenset(
        camera_id for camera_id in camera_ids if camera_path_name(camera_id) not in existing_names
    )

    orphan_ids = [
        camera_id
        for path_name in existing_names.difference(desired_names)
        if (camera_id := camera_id_from_path_name(path_name)) is not None
    ]

    return CameraPathPlan(
        missing_ids=missing_ids,
        orphan_ids=tuple(sorted(orphan_ids, key=str)),
    )


async def run_reconcile_loop(
    interval_seconds: float,
    reconcile: Callable[[], Awaitable[None]],
) -> None:
    while True:
        try:
            await reconcile()
        except Exception:
            logger.exception("reconcile tick failed")
        await asyncio.sleep(interval_seconds)


async def reconcile_once() -> None:
    cameras, commands = await _load_reconcile_state()
    await _reconcile_camera_paths(cameras)
    await _publish_desired_commands(commands)


async def _load_reconcile_state() -> tuple[list[Camera], list[StreamCommand]]:
    async with session_factory() as session:
        result = await session.execute(select(Camera).with_for_update())
        cameras = list(result.scalars().all())
        commands: list[StreamCommand] = []

        for camera in cameras:
            if camera.start_command is None:
                commands.append(StopStream(camera_id=camera.id, revision=camera.runtime_revision))
                continue

            command = parse_start_command(camera.id, camera.start_command)
            if command is None:
                camera.start_command = None
                camera.status = CameraStatus.ERROR
                commands.append(StopStream(camera_id=camera.id, revision=camera.runtime_revision))
                continue

            if command.revision != camera.runtime_revision:
                command = command.model_copy(update={"revision": camera.runtime_revision})
                camera.start_command = command.model_dump(mode="json")

            if _errored_start_backed_off(camera):
                continue

            commands.append(command)

        await session.commit()

        return cameras, commands


def _errored_start_backed_off(camera: Camera) -> bool:
    """Space out restarts of a permanently failing run instead of retrying every tick."""
    if camera.status != CameraStatus.ERROR:
        return False

    now = datetime.now(UTC)
    if not runtime_state.worker_retry_ready(camera.id, camera.runtime_revision, now):
        return True

    runtime_state.note_worker_retry(
        camera.id,
        camera.runtime_revision,
        now,
        base_seconds=settings.reconcile_interval_seconds,
        cap_seconds=_MAX_RETRY_BACKOFF_SECONDS,
    )

    return False


async def _reconcile_camera_paths(cameras: Sequence[Camera]) -> None:
    try:
        existing_names = await list_path_names()
    except httpx.HTTPError:
        logger.exception("mediamtx path listing failed")
        return

    plan = plan_camera_paths([camera.id for camera in cameras], existing_names)

    # Existing paths may still carry an old source after a failed post-commit
    # update. The media adapter compares configuration before replacing a path.
    await apply_camera_runtime_plan(
        CameraRuntimePlan(upsert_path_ids={camera.id for camera in cameras})
    )

    for camera_id in plan.orphan_ids:
        await _delete_orphan_camera_path(camera_id)


async def _delete_orphan_camera_path(camera_id: UUID) -> None:
    async with session_factory() as session:
        existing_camera_id = await session.scalar(select(Camera.id).where(Camera.id == camera_id))

    if existing_camera_id is None:
        await delete_camera_path(camera_id)


async def _publish_desired_commands(commands: Sequence[StreamCommand]) -> None:
    for command in commands:
        try:
            await publish_stream_command(command)
            logger.debug("reconciled command type=%s camera=%s", command.type, command.camera_id)
        except Exception:
            logger.exception("reconcile failed for camera %s", command.camera_id)
