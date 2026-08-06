from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from uuid import UUID

    from fastapi import WebSocket

logger = logging.getLogger(__name__)

_SEND_TIMEOUT_SECONDS = 1.0


class CameraBroadcaster:
    """In-process pub/sub for per-camera realtime updates pushed to browser WebSockets."""

    def __init__(self) -> None:
        self._rooms: dict[UUID, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def join(self, camera_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            self._rooms[camera_id].add(websocket)

    async def leave(self, camera_id: UUID, websocket: WebSocket) -> None:
        async with self._lock:
            self._rooms.get(camera_id, set()).discard(websocket)

    async def publish(self, camera_id: UUID, payload: dict[str, Any]) -> None:
        async with self._lock:
            sockets = list(self._rooms.get(camera_id, ()))

        if not sockets:
            return

        results = await asyncio.gather(
            *(
                asyncio.wait_for(websocket.send_json(payload), _SEND_TIMEOUT_SECONDS)
                for websocket in sockets
            ),
            return_exceptions=True,
        )

        dead = [
            websocket
            for websocket, result in zip(sockets, results, strict=True)
            if isinstance(result, BaseException)
        ]

        if not dead:
            return

        logger.warning(
            "websocket send failed for camera %s; evicting %d socket(s)",
            camera_id,
            len(dead),
        )

        async with self._lock:
            room = self._rooms.get(camera_id)

            if room is not None:
                room.difference_update(dead)


broadcaster = CameraBroadcaster()
