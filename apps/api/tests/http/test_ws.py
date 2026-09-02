"""Per-camera realtime WebSocket: session check, camera check, room membership."""

from uuid import uuid4

import pytest
from starlette.websockets import WebSocketDisconnect

from api.adapters.persistence.models import Camera, Workflow
from api.domain.enums import CameraSource
from api.entrypoints.http.routers import ws


class FakeBroadcaster:
    def __init__(self):
        self.joined = []
        self.left = []

    async def join(self, camera_id, websocket):
        self.joined.append(camera_id)

    async def leave(self, camera_id, websocket):
        self.left.append(camera_id)


@pytest.fixture
def rooms(monkeypatch):
    fake = FakeBroadcaster()
    monkeypatch.setattr(ws, "broadcaster", fake)

    return fake


@pytest.fixture
def camera(fake_session):
    workflow = Workflow(name="Doorway", graph={})
    fake_session.seed(workflow)
    row = Camera(
        workflow_id=workflow.id,
        node_id="cam",
        name="Front door",
        source_type=CameraSource.RTSP,
        source_url="rtsp://cam/stream",
    )
    fake_session.seed(row)

    return row


def test_anonymous_socket_is_closed_with_policy_violation(client, rooms):
    with (
        pytest.raises(WebSocketDisconnect) as excinfo,
        client.websocket_connect(f"/ws/cameras/{uuid4()}"),
    ):
        pass

    assert excinfo.value.code == 1008
    assert excinfo.value.reason == "authentication required"
    assert rooms.joined == []


def test_unknown_camera_is_refused(client, owner, rooms):
    with (
        pytest.raises(WebSocketDisconnect) as excinfo,
        client.websocket_connect(f"/ws/cameras/{uuid4()}"),
    ):
        pass

    assert excinfo.value.code == 1008
    assert excinfo.value.reason == "unknown camera"


def test_authenticated_socket_joins_and_leaves_the_camera_room(client, owner, rooms, camera):
    with client.websocket_connect(f"/ws/cameras/{camera.id}"):
        joined_while_open = list(rooms.joined)

    assert joined_while_open == [camera.id]
    assert rooms.left == [camera.id]
