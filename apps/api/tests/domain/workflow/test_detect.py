"""Detect node payload: parameter bounds and event-kind gating."""

import pytest
from pydantic import ValidationError

from api.domain.workflow.detect import DetectData, RunnableDetectData


def test_defaults_to_no_model_and_one_frame_per_second():
    data = DetectData()

    assert data.kind == "detect"
    assert data.model_id is None
    assert data.event_kinds == []
    assert data.confidence_threshold == 0.5
    assert data.inference_fps == 1


@pytest.mark.parametrize(
    "fields",
    [
        {"model_id": "yolo-v8_n"},
        {"event_kinds": ["PERSON_DETECTED", "CAR_DETECTED"]},
        {"confidence_threshold": 0.0},
        {"confidence_threshold": 1.0},
        {"inference_fps": 15},
    ],
    ids=["model_id", "event_kinds", "threshold_zero", "threshold_one", "max_fps"],
)
def test_accepts_valid_fields(fields):
    data = DetectData(**fields)

    for name, value in fields.items():
        assert getattr(data, name) == value


@pytest.mark.parametrize(
    "fields",
    [
        {"model_id": "Yolo"},
        {"model_id": ""},
        {"model_id": "x" * 65},
        {"event_kinds": ["person_detected"]},
        {"event_kinds": ["A"] * 65},
        {"confidence_threshold": 1.01},
        {"confidence_threshold": -0.01},
        {"inference_fps": 0},
        {"inference_fps": 16},
        {"inference_fps": 2.5},
        {"kind": "camera_source"},
        {"unknown": 1},
    ],
    ids=[
        "uppercase_model_id",
        "empty_model_id",
        "long_model_id",
        "lowercase_event_kind",
        "too_many_event_kinds",
        "threshold_above_one",
        "threshold_below_zero",
        "zero_fps",
        "fps_above_fifteen",
        "fractional_fps",
        "foreign_kind",
        "unknown_field",
    ],
)
def test_rejects_invalid_fields(fields):
    with pytest.raises(ValidationError):
        DetectData(**fields)


@pytest.mark.parametrize(
    ("event_kinds", "kind", "expected"),
    [
        ([], "PERSON_DETECTED", True),
        (["PERSON_DETECTED"], "PERSON_DETECTED", True),
        (["CAR_DETECTED", "PERSON_DETECTED"], "PERSON_DETECTED", True),
        (["CAR_DETECTED"], "PERSON_DETECTED", False),
    ],
    ids=["unfiltered", "selected", "one_of_many", "unselected"],
)
def test_passes_gates_on_selected_event_kinds(make_event, event_kinds, kind, expected):
    data = DetectData(event_kinds=event_kinds)
    event = make_event(kind=kind)

    assert data.passes(event) is expected


def test_runnable_requires_a_model():
    with pytest.raises(ValidationError, match="model_id"):
        RunnableDetectData()


def test_runnable_rejects_explicit_null_model():
    with pytest.raises(ValidationError, match="model_id"):
        RunnableDetectData(model_id=None)


def test_runnable_accepts_a_configured_draft():
    draft = DetectData(model_id="yolo", inference_fps=5, event_kinds=["PERSON_DETECTED"])

    runnable = RunnableDetectData.model_validate(draft.model_dump())

    assert runnable.model_id == "yolo"
    assert runnable.inference_fps == 5
    assert runnable.event_kinds == ["PERSON_DETECTED"]
