from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from shared import Detection, DetectionFrame, StartStream, WorkerErrored, WorkerStarted

if TYPE_CHECKING:
    import numpy as np
    import supervision as sv

    from inference.application.ports import (
        DetectionModel,
        DetectionTracker,
        FrameSource,
        FrameSourceFactory,
        InferenceOutput,
        JpegEncoder,
        LastFrameStore,
        ModelRegistry,
        TrackerFactory,
    )

logger = logging.getLogger(__name__)

_MAX_REASON_LENGTH = 200


def run_identity_fields(command: StartStream, *, revision: int | None = None) -> dict[str, Any]:
    """Identity kwargs every run-scoped event carries, stamped with the current time."""
    return {
        "camera_id": command.camera_id,
        "workflow_id": command.workflow_id,
        "revision": command.revision if revision is None else revision,
        "run_id": command.run_id,
        "model_id": command.config.model_id,
        "timestamp": datetime.now(UTC),
    }


@dataclass(frozen=True, slots=True)
class WorkerDependencies:
    models: ModelRegistry
    frame_sources: FrameSourceFactory
    output: InferenceOutput
    last_frames: LastFrameStore
    encode_jpeg: JpegEncoder
    tracker_factory: TrackerFactory
    first_frame_timeout_seconds: float


class CameraWorker:
    """Run the detect-track-publish use case for one camera."""

    def __init__(self, command: StartStream, dependencies: WorkerDependencies) -> None:
        self._command = command
        self._camera_id = command.camera_id
        self._config = command.config
        self._dependencies = dependencies
        self._active = False
        self._reader: FrameSource | None = None
        self._lifecycle_lock = asyncio.Lock()

    async def run(self) -> None:
        reader: FrameSource | None = None
        stage = "model load"

        try:
            detector = await self._dependencies.models.get(self._config.model_id)

            stage = "worker setup"
            tracker = self._dependencies.tracker_factory(float(self._config.inference_fps))
            reader = self._dependencies.frame_sources.create(
                self._camera_id,
                self._config.inference_fps,
            )
            self._reader = reader
            reader.start()

            try:
                frame = await asyncio.wait_for(
                    reader.next_frame(),
                    timeout=self._dependencies.first_frame_timeout_seconds,
                )
            except TimeoutError:
                timeout = self._dependencies.first_frame_timeout_seconds
                logger.warning(
                    "no first frame camera=%s timeout=%.1fs",
                    self._camera_id,
                    timeout,
                )
                await self._publish_errored_safely(f"no frames from stream within {timeout:g}s")
                return

            stage = "worker start"
            await self._publish_started()
            logger.info("worker running camera=%s", self._camera_id)

            stage = "inference"
            while True:
                detections = await asyncio.to_thread(
                    _detect_and_track,
                    detector,
                    tracker,
                    frame,
                    self._config.confidence_threshold,
                )
                await self._publish_frame(detector, detections, frame)

                try:
                    frame = await asyncio.wait_for(
                        reader.next_frame(),
                        timeout=self._dependencies.first_frame_timeout_seconds,
                    )
                except TimeoutError:
                    timeout = self._dependencies.first_frame_timeout_seconds
                    logger.warning(
                        "stream stalled camera=%s timeout=%.1fs",
                        self._camera_id,
                        timeout,
                    )
                    await self._publish_errored_safely(f"no frames from stream for {timeout:g}s")
                    return
        except asyncio.CancelledError:
            logger.info("worker cancelled camera=%s", self._camera_id)
            raise
        except Exception as exc:
            logger.exception("worker failed camera=%s stage=%s", self._camera_id, stage)
            await self._publish_errored_safely(self._failure_reason(stage, exc))
        finally:
            self._reader = None

            if reader is not None:
                try:
                    await reader.stop()
                except Exception:
                    logger.exception("frame source cleanup failed camera=%s", self._camera_id)

            await self._deactivate()

    async def replay_started(self) -> bool:
        """Republish active state when desired-state reconciliation repeats a command."""
        async with self._lifecycle_lock:
            if not self._active:
                return False

            await self._publish_started_event()

            return True

    async def apply(self, command: StartStream) -> bool:
        """Adopt a same-model desired run in place instead of restarting the pipeline."""
        if command.config.model_id != self._config.model_id:
            return False

        async with self._lifecycle_lock:
            if not self._active or self._reader is None:
                return False

            self._command = command
            self._config = command.config
            self._reader.set_target_fps(command.config.inference_fps)
            await self._publish_started_event()

            return True

    async def _publish_frame(
        self,
        detector: DetectionModel,
        detections: sv.Detections,
        frame: np.ndarray,
    ) -> None:
        frame_height, frame_width = frame.shape[:2]

        jpeg = await asyncio.to_thread(self._dependencies.encode_jpeg, frame)
        if jpeg is not None:
            await self._dependencies.last_frames.put(self._camera_id, jpeg)

        await self._dependencies.output.publish_detection_frame(
            DetectionFrame(
                **run_identity_fields(self._command),
                frame_width=frame_width,
                frame_height=frame_height,
                detections=_to_schema(detector, detections),
            )
        )

    async def _publish_started(self) -> None:
        async with self._lifecycle_lock:
            await self._publish_started_event()
            self._active = True

    async def _publish_started_event(self) -> None:
        await self._dependencies.output.publish_worker_event(
            WorkerStarted(**run_identity_fields(self._command))
        )

    async def _publish_errored(self, reason: str) -> None:
        async with self._lifecycle_lock:
            self._active = False
            await self._dependencies.output.publish_worker_event(
                WorkerErrored(**run_identity_fields(self._command), reason=reason)
            )

    async def _publish_errored_safely(self, reason: str) -> None:
        try:
            await self._publish_errored(reason)
        except Exception:
            logger.exception("errored-event publish failed camera=%s", self._camera_id)

    async def _deactivate(self) -> None:
        async with self._lifecycle_lock:
            self._active = False

    def _failure_reason(self, stage: str, exc: Exception) -> str:
        if stage == "model load":
            return f"model load failed: {self._config.model_id}"

        reason = str(exc)[:_MAX_REASON_LENGTH]
        if not reason:
            return f"{stage} failed: {type(exc).__name__}"

        return reason


def _detect_and_track(
    detector: DetectionModel,
    tracker: DetectionTracker,
    frame: np.ndarray,
    confidence_threshold: float,
) -> sv.Detections:
    detections = detector.detect(frame)
    confidence = _required_field(detections.confidence, "confidence")

    return tracker.update(detections[confidence >= confidence_threshold])


def _to_schema(detector: DetectionModel, detections: sv.Detections) -> list[Detection]:
    if len(detections) == 0:
        return []

    confidence = _required_field(detections.confidence, "confidence")
    class_ids = _required_field(detections.class_id, "class_id")

    untracked = [-1] * len(detections)
    tracker_ids = untracked if detections.tracker_id is None else detections.tracker_id

    return [
        Detection(
            label=detector.label_for(int(class_id)),
            bounding_box=(float(box[0]), float(box[1]), float(box[2]), float(box[3])),
            confidence=float(row_confidence),
            class_id=int(class_id),
            tracker_id=int(tracker_id) if tracker_id >= 0 else None,
        )
        for box, row_confidence, class_id, tracker_id in zip(
            detections.xyxy,
            confidence,
            class_ids,
            tracker_ids,
            strict=True,
        )
    ]


def _required_field[Value](value: Value | None, name: str) -> Value:
    if value is None:
        raise ValueError(f"detections are missing {name}; model adapters must always set it")

    return value
