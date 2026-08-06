from __future__ import annotations

import asyncio
import contextlib
import logging
from dataclasses import dataclass
from functools import partial
from typing import TYPE_CHECKING

from inference.application.worker import run_identity_fields
from shared import StartStream, StopStream, StreamCommand, WorkerStopped

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

    from inference.application.ports import InferenceOutput, WorkerFactory, WorkerRunner

logger = logging.getLogger(__name__)

_REAP_TIMEOUT_SECONDS = 30.0


@dataclass(slots=True)
class _RunningCamera:
    task: asyncio.Task[None]
    command: StartStream
    worker: WorkerRunner


def _is_same_active_run(running: _RunningCamera, command: StartStream) -> bool:
    if running.task.done():
        return False

    return running.command == command


class WorkerPool:
    """Own one detection task per camera and fence commands by desired revision."""

    def __init__(self, worker_factory: WorkerFactory, output: InferenceOutput) -> None:
        self._worker_factory = worker_factory
        self._output = output
        self._cameras: dict[UUID, _RunningCamera] = {}
        self._desired: dict[UUID, StreamCommand] = {}
        self._lock = asyncio.Lock()

    async def start_camera(self, command: StartStream) -> None:
        replay_worker: WorkerRunner | None = None
        replaced_camera: _RunningCamera | None = None
        applied_in_place = False

        async with self._lock:
            desired = self._desired.get(command.camera_id)
            if desired is not None:
                if command.revision < desired.revision:
                    logger.info(
                        "ignoring stale start camera=%s revision=%d latest=%d",
                        command.camera_id,
                        command.revision,
                        desired.revision,
                    )
                    return

                if command.revision == desired.revision and command != desired:
                    logger.warning(
                        "ignoring conflicting start camera=%s revision=%d",
                        command.camera_id,
                        command.revision,
                    )
                    return

            self._desired[command.camera_id] = command

            running = self._cameras.get(command.camera_id)
            if running is not None and _is_same_active_run(running, command):
                replay_worker = running.worker
            elif (
                running is not None
                and not running.task.done()
                and await running.worker.apply(command)
            ):
                running.command = command
                applied_in_place = True
            else:
                replaced_camera = self._cancel(command.camera_id)
                worker = self._worker_factory(command)
                task = asyncio.create_task(worker.run(), name=f"camera:{command.camera_id}")
                task.add_done_callback(partial(self._discard_finished, command.camera_id))
                self._cameras[command.camera_id] = _RunningCamera(task, command, worker)

        if applied_in_place:
            logger.info(
                "camera config applied in place id=%s run=%s",
                command.camera_id,
                command.run_id,
            )
            return

        if replaced_camera is not None:
            await self._reap(replaced_camera)

        if replay_worker is not None:
            if await replay_worker.replay_started():
                logger.info("camera active state replayed id=%s", command.camera_id)
            else:
                logger.debug("camera already starting id=%s", command.camera_id)
            return

        logger.info("camera started id=%s workflow=%s", command.camera_id, command.workflow_id)

    async def stop_camera(self, command: StopStream) -> None:
        async with self._lock:
            desired = self._desired.get(command.camera_id)
            if desired is not None:
                if command.revision < desired.revision:
                    logger.info(
                        "ignoring stale stop camera=%s revision=%d latest=%d",
                        command.camera_id,
                        command.revision,
                        desired.revision,
                    )
                    return

                if command.revision == desired.revision:
                    if isinstance(desired, StopStream):
                        return

                    if command.run_id is not None and command.run_id != desired.run_id:
                        logger.info(
                            "ignoring stale targeted stop camera=%s run=%s active_run=%s",
                            command.camera_id,
                            command.run_id,
                            desired.run_id,
                        )
                        return

            cancel_run_id = command.run_id
            if desired is None or command.revision > desired.revision:
                cancel_run_id = None

            self._desired[command.camera_id] = command
            stopped_camera = self._cancel(command.camera_id, cancel_run_id)

        if stopped_camera is None:
            return

        await self._reap(stopped_camera)
        await self._publish_stopped(stopped_camera.command, command.revision)
        logger.info("camera stopped id=%s run=%s", command.camera_id, command.run_id)

    async def shutdown(self) -> None:
        """Cancel all workers without publishing explicit-stop lifecycle events."""
        async with self._lock:
            running = [camera for camera in self._cameras.values() if not camera.task.done()]
            for camera in running:
                camera.task.cancel()

            try:
                async with asyncio.timeout(_REAP_TIMEOUT_SECONDS):
                    results = await asyncio.gather(
                        *(camera.task for camera in running),
                        return_exceptions=True,
                    )
                    self._log_shutdown_errors(running, results)
            except TimeoutError:
                logger.error("worker pool shutdown timed out after %.0fs", _REAP_TIMEOUT_SECONDS)

            self._cameras.clear()
            self._desired.clear()

        logger.info("worker pool shutdown cameras=%d", len(running))

    @staticmethod
    def _log_shutdown_errors(
        running: Sequence[_RunningCamera],
        results: Sequence[object],
    ) -> None:
        for camera, result in zip(running, results, strict=True):
            if isinstance(result, BaseException) and not isinstance(result, asyncio.CancelledError):
                logger.error(
                    "worker raised during shutdown camera=%s: %r",
                    camera.command.camera_id,
                    result,
                )

    async def _publish_stopped(self, command: StartStream, stop_revision: int) -> None:
        await self._output.publish_worker_event(
            WorkerStopped(**run_identity_fields(command, revision=stop_revision))
        )

    def _cancel(
        self,
        camera_id: UUID,
        run_id: UUID | None = None,
    ) -> _RunningCamera | None:
        camera = self._cameras.get(camera_id)
        if camera is None:
            return None

        if run_id is not None and camera.command.run_id != run_id:
            logger.debug(
                "ignoring stale stop camera=%s requested_run=%s active_run=%s",
                camera_id,
                run_id,
                camera.command.run_id,
            )

            return None

        del self._cameras[camera_id]

        if camera.task.done():
            return None

        camera.task.cancel()

        return camera

    async def _reap(self, camera: _RunningCamera) -> None:
        """Await a cancelled worker without holding the pool lock; never wait forever."""
        try:
            async with asyncio.timeout(_REAP_TIMEOUT_SECONDS):
                with contextlib.suppress(asyncio.CancelledError):
                    await camera.task
        except TimeoutError:
            logger.error(
                "worker did not stop within %.0fs camera=%s",
                _REAP_TIMEOUT_SECONDS,
                camera.command.camera_id,
            )

    def _discard_finished(self, camera_id: UUID, task: asyncio.Task[None]) -> None:
        if not task.cancelled() and (exc := task.exception()) is not None:
            logger.error("worker task died camera=%s: %r", camera_id, exc)

        camera = self._cameras.get(camera_id)
        if camera is not None and camera.task is task:
            del self._cameras[camera_id]
