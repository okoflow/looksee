"""In-process per-camera fan-out to WebSocket clients."""

from uuid import uuid4

import pytest

from api.adapters.realtime.broadcaster import CameraBroadcaster


class FakeSocket:
    def __init__(self, fail=False):
        self.fail = fail
        self.sent = []

    async def send_json(self, payload):
        if self.fail:
            raise RuntimeError("socket closed")
        self.sent.append(payload)


@pytest.fixture
def broadcaster():
    return CameraBroadcaster()


async def test_publish_reaches_only_sockets_in_that_camera_room(broadcaster):
    camera, other_camera = uuid4(), uuid4()
    member, outsider = FakeSocket(), FakeSocket()
    await broadcaster.join(camera, member)
    await broadcaster.join(other_camera, outsider)

    await broadcaster.publish(camera, {"type": "event"})

    assert member.sent == [{"type": "event"}]
    assert outsider.sent == []


async def test_left_socket_stops_receiving(broadcaster):
    camera = uuid4()
    socket = FakeSocket()
    await broadcaster.join(camera, socket)
    await broadcaster.leave(camera, socket)

    await broadcaster.publish(camera, {"type": "event"})

    assert socket.sent == []


async def test_publish_to_an_empty_room_is_a_no_op(broadcaster):
    await broadcaster.publish(uuid4(), {"type": "event"})


async def test_failing_socket_is_evicted_and_healthy_ones_keep_receiving(broadcaster, caplog):
    camera = uuid4()
    healthy, broken = FakeSocket(), FakeSocket(fail=True)
    await broadcaster.join(camera, healthy)
    await broadcaster.join(camera, broken)

    await broadcaster.publish(camera, {"n": 1})
    broken.fail = False
    await broadcaster.publish(camera, {"n": 2})

    assert healthy.sent == [{"n": 1}, {"n": 2}]
    assert broken.sent == []
    assert "evicting 1 socket(s)" in caplog.text


async def test_leaving_an_unknown_room_is_harmless(broadcaster):
    await broadcaster.leave(uuid4(), FakeSocket())
