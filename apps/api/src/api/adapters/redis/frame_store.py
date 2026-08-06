"""Read the most recent camera JPEG that inference keeps in Redis."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from redis.asyncio import Redis

from api.config import settings
from shared import last_frame_key

if TYPE_CHECKING:
    from uuid import UUID

logger = logging.getLogger(__name__)

_redis = Redis.from_url(settings.redis_url, socket_timeout=5.0, socket_connect_timeout=5.0)


async def get_last_frame(camera_id: UUID) -> bytes | None:
    try:
        return await _redis.get(last_frame_key(camera_id))
    except Exception:
        logger.exception("last frame fetch failed camera=%s", camera_id)

        return None


async def close_frame_store() -> None:
    await _redis.aclose()
