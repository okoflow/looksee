from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from uuid import UUID

    import numpy as np
    import supervision as sv

    from shared import DetectionFrame, StartStream, WorkerEvent


class DetectionModel(Protocol):
    def label_for(self, class_id: int) -> str: ...

    def detect(self, frame: np.ndarray) -> sv.Detections: ...


class ModelRegistry(Protocol):
    async def get(self, model_id: str) -> DetectionModel: ...


class DetectionTracker(Protocol):
    def update(self, detections: sv.Detections) -> sv.Detections: ...


class FrameSource(Protocol):
    def start(self) -> None: ...

    def set_target_fps(self, target_fps: int) -> None: ...

    async def next_frame(self) -> np.ndarray: ...

    async def stop(self) -> None: ...


class FrameSourceFactory(Protocol):
    def create(self, camera_id: UUID, target_fps: int) -> FrameSource: ...


class InferenceOutput(Protocol):
    async def publish_detection_frame(self, frame: DetectionFrame) -> None: ...

    async def publish_worker_event(self, event: WorkerEvent) -> None: ...


class LastFrameStore(Protocol):
    async def put(self, camera_id: UUID, jpeg: bytes) -> None: ...


class WorkerRunner(Protocol):
    async def run(self) -> None: ...

    async def replay_started(self) -> bool: ...

    async def apply(self, command: StartStream) -> bool: ...


type JpegEncoder = Callable[[np.ndarray], bytes | None]
type TrackerFactory = Callable[[float], DetectionTracker]
type WorkerFactory = Callable[[StartStream], WorkerRunner]
