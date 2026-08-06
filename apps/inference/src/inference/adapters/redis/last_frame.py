from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from redis.asyncio import Redis

from shared import last_frame_key

if TYPE_CHECKING:
    from uuid import UUID

logger = logging.getLogger(__name__)


class RedisLastFrameStore:
    """Keep each camera's latest JPEG in Redis for downstream snapshots."""

    def __init__(self, redis_url: str, ttl_seconds: int) -> None:
        self._redis = Redis.from_url(
            redis_url,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
        )
        self._ttl_seconds = ttl_seconds

    async def put(self, camera_id: UUID, jpeg: bytes) -> None:
        try:
            await self._redis.set(
                last_frame_key(camera_id),
                jpeg,
                ex=self._ttl_seconds,
            )
        except Exception:
            logger.exception("last frame publish failed camera=%s", camera_id)

    async def close(self) -> None:
        await self._redis.aclose()
