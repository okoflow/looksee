import json
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import TypeAdapter, ValidationError

from shared import (
    Detection,
    DetectionFrame,
    WorkerErrored,
    WorkerEvent,
    WorkerStarted,
    WorkerStopped,
)

WORKER_EVENT = TypeAdapter(WorkerEvent)
WORKER_EVENT_TYPES = [WorkerStarted, WorkerErrored, WorkerStopped]


@pytest.fixture
def identity():
    return {
        "camera_id": uuid4(),
        "workflow_id": uuid4(),
        "revision": 2,
        "run_id": uuid4(),
        "model_id": "dfine-m-ppe",
        "timestamp": datetime.now(UTC),
    }


@pytest.fixture
def detection_fields():
    return {
        "label": "helmet",
        "bounding_box": (1.0, 2.0, 30.5, 40.0),
        "confidence": 0.9,
        "class_id": 1,
    }


def test_detection_defaults_to_untracked(detection_fields):
    detection = Detection(**detection_fields)

    assert detection.tracker_id is None


@pytest.mark.parametrize("field", ["label", "bounding_box", "confidence", "class_id"])
def test_detection_requires_each_field(detection_fields, field):
    del detection_fields[field]

    with pytest.raises(ValidationError, match=rf"{field}\s+Field required"):
        Detection(**detection_fields)


def test_detection_rejects_unknown_fields(detection_fields):
    with pytest.raises(ValidationError, match="extra_forbidden"):
        Detection(**detection_fields, mask=[])


def test_detection_is_immutable(detection_fields):
    detection = Detection(**detection_fields)

    with pytest.raises(ValidationError, match="frozen_instance"):
        detection.confidence = 0.1


@pytest.mark.parametrize("bounding_box", [(10.0, 0.0, 5.0, 5.0), (0.0, 10.0, 5.0, 5.0)])
def test_detection_rejects_inverted_boxes(detection_fields, bounding_box):
    detection_fields["bounding_box"] = bounding_box

    with pytest.raises(ValidationError, match="minimums must not exceed maximums"):
        Detection(**detection_fields)


def test_detection_accepts_a_point_box(detection_fields):
    detection_fields["bounding_box"] = (5.0, 5.0, 5.0, 5.0)

    detection = Detection(**detection_fields)

    assert detection.bounding_box == (5.0, 5.0, 5.0, 5.0)


@pytest.mark.parametrize("coordinate", [float("nan"), float("inf"), float("-inf")])
def test_detection_rejects_non_finite_coordinates(detection_fields, coordinate):
    detection_fields["bounding_box"] = (0.0, 0.0, coordinate, 1.0)

    with pytest.raises(ValidationError, match="finite_number"):
        Detection(**detection_fields)


@pytest.mark.parametrize("bounding_box", [(0.0, 0.0, 1.0), (0.0, 0.0, 1.0, 1.0, 1.0)])
def test_detection_requires_four_corner_coordinates(detection_fields, bounding_box):
    detection_fields["bounding_box"] = bounding_box

    with pytest.raises(ValidationError, match="bounding_box"):
        Detection(**detection_fields)


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_detection_rejects_confidence_outside_unit_range(detection_fields, confidence):
    detection_fields["confidence"] = confidence

    with pytest.raises(ValidationError, match="confidence"):
        Detection(**detection_fields)


@pytest.mark.parametrize("field", ["class_id", "tracker_id"])
def test_detection_rejects_negative_ids(detection_fields, field):
    detection_fields[field] = -1

    with pytest.raises(ValidationError, match="greater_than_equal"):
        Detection(**detection_fields)


@pytest.mark.parametrize("label", ["", "x" * 129])
def test_detection_rejects_labels_outside_length_bounds(detection_fields, label):
    detection_fields["label"] = label

    with pytest.raises(ValidationError, match="label"):
        Detection(**detection_fields)


def test_detection_round_trips_through_json(detection_fields):
    detection = Detection(**detection_fields, tracker_id=7)

    restored = Detection.model_validate_json(detection.model_dump_json())

    assert restored == detection


def test_detection_frame_carries_identity_and_detections(identity, detection_fields):
    detection = Detection(**detection_fields)

    frame = DetectionFrame(**identity, frame_width=640, frame_height=480, detections=[detection])

    assert frame.detections == (detection,)
    assert frame.run_id == identity["run_id"]
    assert frame.revision == 2


def test_detection_frame_accepts_no_detections(identity):
    frame = DetectionFrame(**identity, frame_width=640, frame_height=480, detections=())

    assert frame.detections == ()


@pytest.mark.parametrize(
    "field",
    [
        "camera_id",
        "workflow_id",
        "revision",
        "run_id",
        "model_id",
        "timestamp",
        "frame_width",
        "frame_height",
        "detections",
    ],
)
def test_detection_frame_requires_each_field(identity, field):
    fields = {**identity, "frame_width": 640, "frame_height": 480, "detections": ()}
    del fields[field]

    with pytest.raises(ValidationError, match=rf"{field}\s+Field required"):
        DetectionFrame(**fields)


def test_detection_frame_rejects_naive_timestamp(identity):
    identity["timestamp"] = datetime.now(UTC).replace(tzinfo=None)

    with pytest.raises(ValidationError, match="timezone_aware"):
        DetectionFrame(**identity, frame_width=640, frame_height=480, detections=())


def test_detection_frame_rejects_non_slug_model_id(identity):
    identity["model_id"] = "DFINE"

    with pytest.raises(ValidationError, match="string_pattern_mismatch"):
        DetectionFrame(**identity, frame_width=640, frame_height=480, detections=())


def test_detection_frame_rejects_negative_revision(identity):
    identity["revision"] = -1

    with pytest.raises(ValidationError, match="greater_than_equal"):
        DetectionFrame(**identity, frame_width=640, frame_height=480, detections=())


@pytest.mark.parametrize("field", ["frame_width", "frame_height"])
def test_detection_frame_requires_positive_dimensions(identity, field):
    dimensions = {"frame_width": 640, "frame_height": 480, field: 0}

    with pytest.raises(ValidationError, match=field):
        DetectionFrame(**identity, **dimensions, detections=())


def test_detection_frame_rejects_unknown_fields(identity):
    with pytest.raises(ValidationError, match="extra_forbidden"):
        DetectionFrame(**identity, frame_width=640, frame_height=480, detections=(), fps=1)


def test_detection_frame_is_immutable(identity):
    frame = DetectionFrame(**identity, frame_width=640, frame_height=480, detections=())

    with pytest.raises(ValidationError, match="frozen_instance"):
        frame.revision = 3


def test_detection_frame_round_trips_through_json(identity, detection_fields):
    tracked = Detection(**detection_fields, tracker_id=7)
    frame = DetectionFrame(**identity, frame_width=640, frame_height=480, detections=(tracked,))

    restored = DetectionFrame.model_validate_json(frame.model_dump_json())

    assert restored == frame
    assert restored.detections[0].tracker_id == 7


def test_detection_frame_serializes_timestamp_in_utc(identity):
    frame = DetectionFrame(**identity, frame_width=640, frame_height=480, detections=())

    payload = json.loads(frame.model_dump_json())

    assert payload["timestamp"].endswith("Z")


@pytest.mark.parametrize(
    ("event_type", "tag"),
    [
        (WorkerStarted, "worker_started"),
        (WorkerErrored, "worker_errored"),
        (WorkerStopped, "worker_stopped"),
    ],
)
def test_worker_events_tag_their_type(identity, event_type, tag):
    event = event_type(**identity)

    assert event.type == tag


@pytest.mark.parametrize("event_type", WORKER_EVENT_TYPES)
def test_worker_event_dispatches_on_type_tag(identity, event_type):
    event = event_type(**identity)

    parsed = WORKER_EVENT.validate_json(event.model_dump_json())

    assert parsed == event
    assert type(parsed) is event_type


def test_worker_event_rejects_unknown_type_tag(identity):
    payload = {**identity, "type": "worker_paused"}

    with pytest.raises(ValidationError, match="union_tag_invalid"):
        WORKER_EVENT.validate_python(payload)


def test_worker_errored_reason_is_optional(identity):
    event = WorkerErrored(**identity)

    assert event.reason is None


def test_worker_errored_caps_reason_length(identity):
    with pytest.raises(ValidationError, match="string_too_long"):
        WorkerErrored(**identity, reason="x" * 501)


def test_worker_started_rejects_unknown_fields(identity):
    with pytest.raises(ValidationError, match="extra_forbidden"):
        WorkerStarted(**identity, reason="boom")


@pytest.mark.parametrize("event_type", WORKER_EVENT_TYPES)
def test_worker_events_are_immutable(identity, event_type):
    event = event_type(**identity)

    with pytest.raises(ValidationError, match="frozen_instance"):
        event.revision = 9


@pytest.mark.parametrize("event_type", WORKER_EVENT_TYPES)
def test_worker_events_require_run_identity(identity, event_type):
    del identity["run_id"]

    with pytest.raises(ValidationError, match=r"run_id\s+Field required"):
        event_type(**identity)
