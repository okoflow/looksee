"""Thin Redis transport entrypoints."""

import logging
import os
import socket

from faststream.redis import RedisRouter, StreamSub

from api.adapters.persistence.db import session_factory
from api.application.frame_processing import handle_detection_frame
from api.application.worker_status import apply_worker_event
from api.config import settings
from shared import Channel, DetectionFrame, WorkerEvent

logger = logging.getLogger(__name__)

_CONSUMER_NAME = f"{socket.gethostname()}-{os.getpid()}"
router = RedisRouter()


@router.subscriber(
    stream=StreamSub(
        Channel.DETECTION_FRAMES,
        group=settings.consumer_group,
        consumer=_CONSUMER_NAME,
    ),
)
async def consume_detection_frame(frame: DetectionFrame) -> None:
    await handle_detection_frame(frame)


@router.subscriber(channel=Channel.WORKER_EVENTS)
async def consume_worker_event(event: WorkerEvent) -> None:
    try:
        async with session_factory() as session:
            await apply_worker_event(session, event)
    except Exception:
        logger.exception("worker event handling failed camera=%s", event.camera_id)
