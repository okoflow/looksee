from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

from faststream.redis import RedisRouter, StreamSub

from shared import Channel, DetectionFrame, WorkerEvent

if TYPE_CHECKING:
    from pydantic import BaseModel

_DETECTION_FRAMES_MAXLEN = 10_000

publisher_router = RedisRouter()

_detection_frames = publisher_router.publisher(
    stream=StreamSub(Channel.DETECTION_FRAMES, maxlen=_DETECTION_FRAMES_MAXLEN),
    schema=DetectionFrame,
)
_worker_events = publisher_router.publisher(
    channel=Channel.WORKER_EVENTS,
    schema=WorkerEvent,
)


class MessagePublisher(Protocol):
    """FastStream publisher bound to one channel or stream."""

    async def publish(self, message: BaseModel) -> object: ...


class FastStreamInferenceOutput:
    """Publish normalized inference application output through FastStream."""

    def __init__(self, detection_frames: MessagePublisher, worker_events: MessagePublisher) -> None:
        self._detection_frames = detection_frames
        self._worker_events = worker_events

    async def publish_detection_frame(self, frame: DetectionFrame) -> None:
        await self._detection_frames.publish(frame)

    async def publish_worker_event(self, event: WorkerEvent) -> None:
        await self._worker_events.publish(event)


inference_output = FastStreamInferenceOutput(_detection_frames, _worker_events)
