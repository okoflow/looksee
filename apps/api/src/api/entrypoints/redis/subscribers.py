"""Thin Redis transport entrypoints."""

import asyncio
import logging
import os
import socket

from faststream.middlewares.acknowledgement.config import AckPolicy
from faststream.redis import RedisRouter, StreamSub

from api.adapters.persistence.db import session_factory
from api.application.errors import RetryableFrameError
from api.application.frame_processing import FrameProcessingDependencies, handle_detection_frame
from api.application.worker_status import apply_worker_event
from api.config import settings
from shared import Channel, DetectionFrame, WorkerEvent

logger = logging.getLogger(__name__)

_CONSUMER_NAME = f"{socket.gethostname()}-{os.getpid()}"
_RECOVERY_IDLE_MS = 60_000


def create_router(dependencies: FrameProcessingDependencies) -> RedisRouter:
    router = RedisRouter()
    frame_lock = asyncio.Lock()

    @router.subscriber(
        stream=StreamSub(
            Channel.DETECTION_FRAMES,
            group=settings.consumer_group,
            consumer=_CONSUMER_NAME,
            max_records=1,
        ),
        ack_policy=AckPolicy.NACK_ON_ERROR,
        max_workers=1,
    )
    async def consume_detection_frame(frame: DetectionFrame) -> None:
        await process_detection_frame(frame)

    @router.subscriber(
        stream=StreamSub(
            Channel.DETECTION_FRAMES,
            group=settings.consumer_group,
            consumer=f"{_CONSUMER_NAME}-recovery",
            min_idle_time=_RECOVERY_IDLE_MS,
            max_records=1,
        ),
        ack_policy=AckPolicy.NACK_ON_ERROR,
        max_workers=1,
    )
    async def recover_detection_frame(frame: DetectionFrame) -> None:
        await process_detection_frame(frame)

    async def process_detection_frame(frame: DetectionFrame) -> None:
        async with frame_lock:
            while True:
                try:
                    await handle_detection_frame(frame, dependencies)
                    return
                except RetryableFrameError:
                    logger.warning("retrying frame camera=%s", frame.camera_id)
                    await asyncio.sleep(2)

    @router.subscriber(channel=Channel.WORKER_EVENTS)
    async def consume_worker_event(event: WorkerEvent) -> None:
        try:
            async with session_factory() as session:
                await apply_worker_event(session, event)
        except Exception:
            logger.exception("worker event handling failed camera=%s", event.camera_id)

    return router
