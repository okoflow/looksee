"""Per-camera realtime WebSocket entrypoint."""

from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketException, status
from sqlalchemy import select

from api.adapters.persistence.db import session_factory
from api.adapters.persistence.models import Camera, User
from api.adapters.realtime.broadcaster import broadcaster
from api.adapters.security import decode_session_token
from api.entrypoints.http.dependencies import SESSION_COOKIE

router = APIRouter(prefix="/ws", tags=["ws"])


@router.websocket("/cameras/{camera_id}")
async def camera_socket(websocket: WebSocket, camera_id: UUID) -> None:
    if not await _socket_authenticated(websocket):
        raise WebSocketException(
            code=status.WS_1008_POLICY_VIOLATION, reason="authentication required"
        )

    if not await _camera_exists(camera_id):
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="unknown camera")

    await websocket.accept()
    await broadcaster.join(camera_id, websocket)
    try:
        await _drain_until_disconnect(websocket)
    finally:
        await broadcaster.leave(camera_id, websocket)


async def _socket_authenticated(websocket: WebSocket) -> bool:
    token = websocket.cookies.get(SESSION_COOKIE)
    user_id = decode_session_token(token) if token is not None else None
    if user_id is None:
        return False

    async with session_factory() as session:
        return await session.get(User, user_id) is not None


async def _camera_exists(camera_id: UUID) -> bool:
    async with session_factory() as session:
        known_camera_id = await session.scalar(select(Camera.id).where(Camera.id == camera_id))

    return known_camera_id is not None


async def _drain_until_disconnect(websocket: WebSocket) -> None:
    """Ignore inbound frames of any type; the socket is broadcast-only."""
    while True:
        message = await websocket.receive()

        if message["type"] == "websocket.disconnect":
            return
