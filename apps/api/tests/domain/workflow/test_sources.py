"""Camera source payload and its per-source-type runnable refinements."""

import pytest
from pydantic import TypeAdapter, ValidationError

from api.domain.enums import CameraSource
from api.domain.workflow.sources import (
    CameraSourceData,
    RunnableCameraSourceData,
    RunnableFileSource,
    RunnableRtmpSource,
    RunnableRtspSource,
    RunnableSrtSource,
    RunnableWebrtcSource,
    RunnableWhepSource,
)

runnable_adapter = TypeAdapter(RunnableCameraSourceData)


def to_runnable(draft):
    return runnable_adapter.validate_python(draft.model_dump())


def test_defaults_to_an_unconfigured_rtsp_camera():
    data = CameraSourceData()

    assert data.kind == "camera_source"
    assert data.name == "Camera"
    assert data.source_type is CameraSource.RTSP
    assert data.url == ""


def test_source_type_accepts_enum_values_as_strings():
    data = CameraSourceData(source_type="file", url="clips/demo.mp4")

    assert data.source_type is CameraSource.FILE


def test_draft_accepts_any_url_text():
    data = CameraSourceData(url="not a url at all")

    assert data.url == "not a url at all"


@pytest.mark.parametrize(
    "fields",
    [
        {"source_type": "hls"},
        {"name": ""},
        {"name": "x" * 129},
        {"url": "x" * 2049},
        {"kind": "detect"},
        {"path": "clips/demo.mp4"},
    ],
    ids=[
        "unknown_source_type",
        "empty_name",
        "long_name",
        "long_url",
        "foreign_kind",
        "unknown_field",
    ],
)
def test_draft_rejects_invalid_fields(fields):
    with pytest.raises(ValidationError):
        CameraSourceData(**fields)


@pytest.mark.parametrize(
    ("source_type", "url", "runnable_type"),
    [
        ("rtsp", "rtsp://cam.local/stream", RunnableRtspSource),
        ("rtsp", "rtsps://cam.local:8554/stream", RunnableRtspSource),
        ("rtmp", "rtmp://live.local/app/key", RunnableRtmpSource),
        ("rtmp", "rtmps://live.local/app/key", RunnableRtmpSource),
        ("srt", "srt://relay.local:9000", RunnableSrtSource),
        ("webrtc", "", RunnableWebrtcSource),
        ("whep", "https://sfu.local/whep/cam", RunnableWhepSource),
        ("whep", "http://sfu.local/whep/cam", RunnableWhepSource),
        ("whep", "whep://sfu.local/cam", RunnableWhepSource),
        ("whep", "wheps://sfu.local/cam", RunnableWhepSource),
        ("file", "clips/demo.mp4", RunnableFileSource),
    ],
)
def test_runnable_dispatches_on_source_type(source_type, url, runnable_type):
    draft = CameraSourceData(source_type=source_type, url=url)

    runnable = to_runnable(draft)

    assert type(runnable) is runnable_type


@pytest.mark.parametrize(
    ("source_type", "url"),
    [
        ("rtsp", ""),
        ("rtsp", "http://cam.local/stream"),
        ("rtsp", "cam.local/stream"),
        ("rtmp", ""),
        ("rtmp", "rtsp://cam.local/x"),
        ("srt", ""),
        ("srt", "udp://relay:9000"),
        ("whep", ""),
        ("whep", "rtsp://sfu.local/x"),
        ("file", ""),
        ("file", "rtsp://cam.local/x"),
    ],
)
def test_runnable_rejects_missing_or_wrong_scheme_url(source_type, url):
    draft = CameraSourceData(source_type=source_type, url=url)

    with pytest.raises(ValidationError, match="url"):
        to_runnable(draft)


def test_runnable_keeps_name_and_url():
    draft = CameraSourceData(name="Lobby", source_type="rtsp", url="rtsp://cam.local/live")

    runnable = to_runnable(draft)

    assert runnable.name == "Lobby"
    assert str(runnable.url) == "rtsp://cam.local/live"


def test_webrtc_source_needs_no_url():
    runnable = RunnableWebrtcSource(source_type=CameraSource.WEBRTC)

    assert runnable.url == ""


def test_webrtc_source_tolerates_a_stale_url():
    draft = CameraSourceData(source_type="webrtc", url="rtsp://left-over")

    runnable = to_runnable(draft)

    assert isinstance(runnable, RunnableWebrtcSource)
    assert runnable.url == "rtsp://left-over"


@pytest.mark.parametrize(
    "path",
    ["x", "demo.mp4", "clips/demo.mp4", "a/b/c/d.mkv", "2026-01-07_cam-1.mp4", "v1.2.3/clip"],
)
def test_file_source_accepts_conservative_object_keys(path):
    runnable = RunnableFileSource(source_type=CameraSource.FILE, url=path)

    assert runnable.url == path


@pytest.mark.parametrize(
    "path",
    [
        "",
        ".hidden",
        "clips/.hidden",
        "../escape",
        "clips/../escape",
        "/absolute",
        "clips//double",
        "clips/",
        "with space.mp4",
        "semi;colon",
        "dollar$var",
        "back\\slash",
        "tab\tname",
        "x" * 1025,
    ],
    ids=[
        "empty",
        "dotfile",
        "nested_dotfile",
        "parent_segment",
        "nested_parent_segment",
        "absolute",
        "double_slash",
        "trailing_slash",
        "space",
        "semicolon",
        "dollar",
        "backslash",
        "tab",
        "too_long",
    ],
)
def test_file_source_rejects_unsafe_object_keys(path):
    with pytest.raises(ValidationError):
        RunnableFileSource(source_type=CameraSource.FILE, url=path)


@pytest.mark.parametrize(
    ("runnable_type", "wrong_type"),
    [
        (RunnableRtspSource, "rtmp"),
        (RunnableRtmpSource, "rtsp"),
        (RunnableSrtSource, "rtsp"),
        (RunnableWebrtcSource, "whep"),
        (RunnableWhepSource, "webrtc"),
        (RunnableFileSource, "rtsp"),
    ],
)
def test_runnable_variants_pin_their_source_type(runnable_type, wrong_type):
    with pytest.raises(ValidationError, match="source_type"):
        runnable_type(source_type=wrong_type, url="rtsp://cam.local/x")
