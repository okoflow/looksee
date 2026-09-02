"""Snapshot evidence: last frame lookup, annotation, and file naming."""

import re
from io import BytesIO

import pytest
from PIL import Image

from api.adapters.actions import snapshots
from api.adapters.actions.snapshots import run_snapshot
from api.config import settings
from api.domain.workflow import SnapshotActionData

FILENAME = re.compile(r"^20260304-120000-[0-9a-f]{8}-[0-9a-f]{8}\.jpg$")


def jpeg_bytes(size=(1280, 720), colour=(90, 90, 90)):
    buffer = BytesIO()
    Image.new("RGB", size, colour).save(buffer, format="JPEG", quality=95)

    return buffer.getvalue()


@pytest.fixture
def frames(monkeypatch, tmp_path):
    holder = {"jpeg": jpeg_bytes()}

    async def get_last_frame(camera_id):
        return holder["jpeg"]

    monkeypatch.setattr(snapshots, "get_last_frame", get_last_frame)
    monkeypatch.setattr(settings, "snapshots_dir", tmp_path)

    return holder


def written_files(tmp_path):
    return sorted(tmp_path.iterdir())


async def test_snapshot_is_written_and_shared_through_the_context(
    frames, tmp_path, identity, make_event
):
    event = make_event()
    context = {}

    await run_snapshot(identity, event, SnapshotActionData(annotate=False), context)

    [path] = written_files(tmp_path)
    assert FILENAME.match(path.name)
    assert event.camera_id.hex[:8] in path.name
    assert path.read_bytes() == frames["jpeg"]
    assert context == {"snapshot_url": f"/snapshots/{path.name}", "snapshot_jpeg": frames["jpeg"]}


async def test_missing_frame_writes_nothing(frames, tmp_path, identity, make_event, caplog):
    frames["jpeg"] = None
    context = {}

    await run_snapshot(identity, make_event(), SnapshotActionData(), context)

    assert written_files(tmp_path) == []
    assert context == {}
    assert "no recent frame for snapshot" in caplog.text


async def test_annotation_draws_each_detection_box(
    frames, tmp_path, identity, make_event, make_detection
):
    event = make_event(detections=[make_detection(bounding_box=(100.0, 100.0, 300.0, 400.0))])

    await run_snapshot(identity, event, SnapshotActionData(annotate=True), {})

    [path] = written_files(tmp_path)
    image = Image.open(BytesIO(path.read_bytes()))
    on_box = image.getpixel((100, 250))
    inside_box = image.getpixel((200, 250))
    assert image.size == (1280, 720)
    assert path.read_bytes() != frames["jpeg"]
    assert on_box[0] > 180 and on_box[1] < 130
    assert all(abs(channel - 90) < 20 for channel in inside_box)


async def test_annotation_is_skipped_without_detections(frames, tmp_path, identity, make_event):
    await run_snapshot(identity, make_event(detections=[]), SnapshotActionData(annotate=True), {})

    [path] = written_files(tmp_path)
    assert path.read_bytes() == frames["jpeg"]


async def test_frame_of_another_size_is_kept_raw(frames, tmp_path, identity, make_event, caplog):
    frames["jpeg"] = jpeg_bytes(size=(640, 360))

    await run_snapshot(identity, make_event(), SnapshotActionData(annotate=True), {})

    [path] = written_files(tmp_path)
    assert path.read_bytes() == frames["jpeg"]
    assert "does not match event frame 1280x720" in caplog.text


async def test_undecodable_frame_is_kept_raw(frames, tmp_path, identity, make_event, caplog):
    frames["jpeg"] = b"not a jpeg"

    await run_snapshot(identity, make_event(), SnapshotActionData(annotate=True), {})

    [path] = written_files(tmp_path)
    assert path.read_bytes() == b"not a jpeg"
    assert "snapshot annotation failed" in caplog.text
