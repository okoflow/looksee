from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from functools import partial
from typing import TYPE_CHECKING

from faststream import ContextRepo, FastStream
from faststream.redis import RedisBroker

from inference.adapters.jpeg import encode_jpeg
from inference.adapters.onnx import DetectorRegistry
from inference.adapters.redis import (
    RedisLastFrameStore,
    inference_output,
    publisher_router,
)
from inference.adapters.tracking import ByteTrackDetectionTracker
from inference.adapters.video import MediaMtxFrameSourceFactory
from inference.application import CameraWorker, WorkerDependencies, WorkerPool
from inference.config import settings
from inference.entrypoints.commands import command_router

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

broker = RedisBroker(settings.redis_url)
last_frames = RedisLastFrameStore(settings.redis_url, settings.last_frame_ttl_seconds)
dependencies = WorkerDependencies(
    models=DetectorRegistry(settings.models_dir),
    frame_sources=MediaMtxFrameSourceFactory(
        base_url=settings.mediamtx_rtsp_url,
        media_user=settings.mtx_media_user,
        media_password=settings.mtx_media_password,
        transport=settings.rtsp_transport,
    ),
    output=inference_output,
    last_frames=last_frames,
    encode_jpeg=encode_jpeg,
    tracker_factory=ByteTrackDetectionTracker,
    first_frame_timeout_seconds=settings.first_frame_timeout_seconds,
)
pool = WorkerPool(
    worker_factory=partial(CameraWorker, dependencies=dependencies),
    output=inference_output,
)


@asynccontextmanager
async def lifespan(context: ContextRepo) -> AsyncIterator[None]:
    context.set_global("pool", pool)
    logger.info("inference ready")
    yield


async def shutdown_runtime() -> None:
    """Stop workers and close the dedicated last-frame Redis client."""
    await pool.shutdown()
    await last_frames.close()


app = FastStream(broker, lifespan=lifespan, on_shutdown=[shutdown_runtime])
broker.include_router(command_router)
broker.include_router(publisher_router)
