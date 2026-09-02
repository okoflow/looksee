"""Model descriptors: validation and event-class projections."""

import pytest
from pydantic import ValidationError

from api.domain.models import ModelClassDescriptor, ModelDescriptor


def make_class(class_id, label, event_kind):
    return ModelClassDescriptor(class_id=class_id, label=label, event_kind=event_kind)


@pytest.fixture
def descriptor():
    classes = (
        make_class(0, "person", "PERSON_DETECTED"),
        make_class(1, "background", None),
        make_class(2, "car", "CAR_DETECTED"),
    )

    return ModelDescriptor(id="yolo-v8", name="YOLO", classes=classes)


def test_event_classes_skip_classes_without_event_kind(descriptor):
    labels = [model_class.label for model_class in descriptor.event_classes()]

    assert labels == ["person", "car"]


def test_events_by_label_maps_only_event_classes(descriptor):
    assert descriptor.events_by_label() == {"person": "PERSON_DETECTED", "car": "CAR_DETECTED"}


def test_descriptor_without_event_classes_has_empty_projections():
    classes = (make_class(0, "thing", None),)

    descriptor = ModelDescriptor(id="plain", name="Plain", classes=classes)

    assert descriptor.event_classes() == ()
    assert descriptor.events_by_label() == {}


def test_threshold_defaults_to_none():
    descriptor = ModelDescriptor(id="yolo", name="YOLO", classes=())

    assert descriptor.recommended_confidence_threshold is None


def test_descriptor_is_frozen(descriptor):
    with pytest.raises(ValidationError):
        descriptor.name = "renamed"


def test_class_descriptor_is_frozen():
    model_class = make_class(0, "person", None)

    with pytest.raises(ValidationError):
        model_class.label = "other"


@pytest.mark.parametrize(
    "fields",
    [
        {"class_id": -1},
        {"label": ""},
        {"label": "x" * 129},
        {"event_kind": "lowercase"},
        {"event_kind": "X" * 65},
        {"extra": 1},
    ],
    ids=[
        "negative_class_id",
        "empty_label",
        "long_label",
        "lowercase_event_kind",
        "long_event_kind",
        "unknown_field",
    ],
)
def test_class_descriptor_rejects_invalid_fields(fields):
    values = {"class_id": 0, "label": "person", "event_kind": None, **fields}

    with pytest.raises(ValidationError):
        ModelClassDescriptor(**values)


def test_class_descriptor_requires_explicit_event_kind():
    with pytest.raises(ValidationError, match="event_kind"):
        ModelClassDescriptor(class_id=0, label="person")


@pytest.mark.parametrize(
    "fields",
    [
        {"id": "Bad Id"},
        {"id": ""},
        {"id": "x" * 65},
        {"name": ""},
        {"name": "x" * 129},
        {"recommended_confidence_threshold": 1.5},
        {"recommended_confidence_threshold": -0.1},
        {"classes": [{"class_id": 0, "label": "a", "event_kind": None, "extra": 1}]},
        {"unknown": True},
    ],
    ids=[
        "id_with_spaces",
        "empty_id",
        "long_id",
        "empty_name",
        "long_name",
        "threshold_above_one",
        "threshold_below_zero",
        "invalid_nested_class",
        "unknown_field",
    ],
)
def test_model_descriptor_rejects_invalid_fields(fields):
    values = {"id": "yolo", "name": "YOLO", "classes": (), **fields}

    with pytest.raises(ValidationError):
        ModelDescriptor(**values)


@pytest.mark.parametrize("threshold", [0.0, 0.5, 1.0])
def test_model_descriptor_accepts_threshold_boundaries(threshold):
    descriptor = ModelDescriptor(
        id="yolo",
        name="YOLO",
        classes=(),
        recommended_confidence_threshold=threshold,
    )

    assert descriptor.recommended_confidence_threshold == threshold
