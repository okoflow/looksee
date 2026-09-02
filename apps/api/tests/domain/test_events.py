"""DetectionEvent contract."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from api.domain.events import EVENT_KIND_DETECTED_SUFFIX, DetectionEvent


def test_detected_suffix_is_stable():
    assert EVENT_KIND_DETECTED_SUFFIX == "_DETECTED"


def test_defaults_to_no_detections_and_empty_metadata(make_event):
    event = make_event()

    assert event.detections == []
    assert event.metadata == {}


def test_keeps_detections_and_metadata(make_event, make_detection):
    detection = make_detection(label="car")

    event = make_event(detections=[detection], metadata={"snapshot_url": "s3://x"})

    assert event.detections == [detection]
    assert event.metadata == {"snapshot_url": "s3://x"}


def test_rejects_naive_timestamp(make_event):
    naive = datetime(2026, 1, 7, 12, 0, tzinfo=UTC).replace(tzinfo=None)

    with pytest.raises(ValidationError, match="timezone"):
        make_event(ts=naive)


def test_keeps_timestamp_offset(make_event):
    aware = datetime.fromisoformat("2026-01-07T12:00:00+02:00")

    event = make_event(ts=aware)

    assert event.ts == aware
    assert event.ts.utcoffset() == aware.utcoffset()


@pytest.mark.parametrize(
    "fields",
    [
        {"frame_width": 0},
        {"frame_height": 0},
        {"frame_width": -1},
        {"kind": "person_detected"},
        {"kind": "1ABC"},
        {"kind": ""},
        {"kind": "A" * 65},
        {"model_id": "Yolo"},
        {"camera_id": "not-a-uuid"},
        {"detections": [{"label": "x"}]},
        {"extra": 1},
    ],
    ids=[
        "zero_width",
        "zero_height",
        "negative_width",
        "lowercase_kind",
        "digit_first_kind",
        "empty_kind",
        "long_kind",
        "uppercase_model_id",
        "bad_camera_id",
        "incomplete_detection",
        "unknown_field",
    ],
)
def test_rejects_invalid_fields(make_event, fields):
    with pytest.raises(ValidationError):
        make_event(**fields)


@pytest.mark.parametrize("field", ["camera_id", "workflow_id", "model_id", "kind", "ts"])
def test_requires_identity_fields(make_event, field):
    event = make_event()
    values = event.model_dump()
    del values[field]

    with pytest.raises(ValidationError, match=field):
        DetectionEvent(**values)


def test_is_frozen(make_event):
    event = make_event()

    with pytest.raises(ValidationError):
        event.kind = "OTHER"
