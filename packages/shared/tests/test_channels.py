from uuid import UUID, uuid4

import pytest

from shared import Channel, camera_id_from_path_name, camera_path_name, last_frame_key

CAMERA_ID = UUID("12345678-1234-5678-1234-567812345678")


def test_channel_names_match_the_wire_protocol():
    assert Channel.STREAM_COMMANDS == "stream.commands"
    assert Channel.WORKER_EVENTS == "worker.events"
    assert Channel.DETECTION_FRAMES == "detection.frames"


def test_channel_renders_as_its_wire_name():
    assert str(Channel.DETECTION_FRAMES) == "detection.frames"


def test_last_frame_key_embeds_camera_id():
    assert last_frame_key(CAMERA_ID) == "frames.last.12345678-1234-5678-1234-567812345678"


def test_camera_path_name_is_the_camera_id():
    assert camera_path_name(CAMERA_ID) == "12345678-1234-5678-1234-567812345678"


def test_camera_id_round_trips_through_path_name():
    camera_id = uuid4()

    path_name = camera_path_name(camera_id)

    assert camera_id_from_path_name(path_name) == camera_id


@pytest.mark.parametrize("path_name", ["", "webcam", "12345678-1234-5678-1234"])
def test_camera_id_from_path_name_returns_none_for_foreign_paths(path_name):
    assert camera_id_from_path_name(path_name) is None
