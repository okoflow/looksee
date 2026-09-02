from dataclasses import FrozenInstanceError
from uuid import UUID

import pytest

from inference.adapters.video import mediamtx
from inference.adapters.video.mediamtx import MediaMtxFrameSourceFactory

CAMERA_ID = UUID("12345678-1234-5678-1234-567812345678")
CAMERA_PATH = "12345678-1234-5678-1234-567812345678"


class FakeReader:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


@pytest.fixture(autouse=True)
def fake_reader(monkeypatch):
    monkeypatch.setattr(mediamtx, "RtspReader", FakeReader)


def make_factory(**overrides) -> MediaMtxFrameSourceFactory:
    fields = {
        "base_url": "rtsp://mediamtx:8554",
        "media_user": "media",
        "media_password": "",
        "transport": "tcp",
    }
    fields.update(overrides)

    return MediaMtxFrameSourceFactory(**fields)


def test_create_wires_reader_with_camera_path_and_transport():
    factory = make_factory(transport="udp")

    reader = factory.create(CAMERA_ID, target_fps=5)

    assert reader.kwargs == {
        "rtsp_url": f"rtsp://mediamtx:8554/{CAMERA_PATH}",
        "target_fps": 5,
        "transport": "udp",
        "source_name": CAMERA_PATH,
    }


def test_url_omits_credentials_without_password():
    factory = make_factory(media_user="media", media_password="")

    url = factory.create(CAMERA_ID, target_fps=1).kwargs["rtsp_url"]

    assert url == f"rtsp://mediamtx:8554/{CAMERA_PATH}"


def test_url_embeds_credentials_when_password_is_set():
    factory = make_factory(media_password="secret")

    url = factory.create(CAMERA_ID, target_fps=1).kwargs["rtsp_url"]

    assert url == f"rtsp://media:secret@mediamtx:8554/{CAMERA_PATH}"


def test_url_escapes_reserved_characters_in_credentials():
    factory = make_factory(media_user="me dia", media_password="p@ss:w/rd?#")

    url = factory.create(CAMERA_ID, target_fps=1).kwargs["rtsp_url"]

    assert url == f"rtsp://me%20dia:p%40ss%3Aw%2Frd%3F%23@mediamtx:8554/{CAMERA_PATH}"


def test_url_keeps_base_path_prefix():
    factory = make_factory(base_url="rtsp://proxy.local:8554/mtx", media_password="pw")

    url = factory.create(CAMERA_ID, target_fps=1).kwargs["rtsp_url"]

    assert url == f"rtsp://media:pw@proxy.local:8554/mtx/{CAMERA_PATH}"


def test_factory_is_immutable():
    factory = make_factory()

    with pytest.raises(FrozenInstanceError):
        factory.transport = "udp"
