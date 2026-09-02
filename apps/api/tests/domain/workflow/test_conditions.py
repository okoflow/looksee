"""If/else condition payloads and their match semantics."""

import pytest
from pydantic import TypeAdapter, ValidationError

from api.domain.workflow.conditions import (
    ConditionModel,
    DetectionCountCondition,
    EventKindCondition,
    IfElseCondition,
    MaxConfidenceCondition,
    ObjectClassCondition,
    RunnableEventKindCondition,
    RunnableIfElseCondition,
    RunnableObjectClassCondition,
    compare_number,
)

condition_adapter = TypeAdapter(IfElseCondition)
runnable_adapter = TypeAdapter(RunnableIfElseCondition)


@pytest.mark.parametrize(
    ("operator", "left", "right", "expected"),
    [
        ("eq", 1, 1, True),
        ("eq", 1, 2, False),
        ("neq", 1, 2, True),
        ("neq", 1, 1, False),
        ("gt", 2, 1, True),
        ("gt", 1, 1, False),
        ("gte", 1, 1, True),
        ("gte", 0, 1, False),
        ("lt", 0, 1, True),
        ("lt", 1, 1, False),
        ("lte", 1, 1, True),
        ("lte", 2, 1, False),
    ],
)
def test_compare_number(operator, left, right, expected):
    assert compare_number(left, operator, right) is expected


def test_base_condition_selects_nothing():
    condition = ConditionModel()

    assert condition.selected_event_kind() is None
    assert condition.selected_class_label() is None


def test_event_kind_condition_defaults_to_unselected():
    condition = EventKindCondition()

    assert condition.field == "event_kind"
    assert condition.operator == "is"
    assert condition.value is None


def test_unselected_event_kind_never_matches(make_event):
    condition = EventKindCondition(operator="is_not")

    assert condition.matches(make_event()) is False
    assert condition.selected_event_kind() is None


@pytest.mark.parametrize(
    ("operator", "kind", "expected"),
    [
        ("is", "PERSON_DETECTED", True),
        ("is", "CAR_DETECTED", False),
        ("is_not", "PERSON_DETECTED", False),
        ("is_not", "CAR_DETECTED", True),
    ],
)
def test_event_kind_condition_matches(make_event, operator, kind, expected):
    condition = EventKindCondition(operator=operator, value="PERSON_DETECTED")
    event = make_event(kind=kind)

    assert condition.matches(event) is expected


def test_event_kind_condition_reports_its_selection():
    condition = EventKindCondition(value="PERSON_DETECTED")

    assert condition.selected_event_kind() == "PERSON_DETECTED"
    assert condition.selected_class_label() is None


@pytest.mark.parametrize(
    "fields",
    [{"operator": "contains"}, {"value": "person"}, {"field": "object_class"}, {"extra": 1}],
    ids=["foreign_operator", "lowercase_value", "foreign_field", "unknown_field"],
)
def test_event_kind_condition_rejects_invalid_fields(fields):
    with pytest.raises(ValidationError):
        EventKindCondition(**fields)


def test_object_class_condition_defaults_to_blank_contains():
    condition = ObjectClassCondition()

    assert condition.field == "object_class"
    assert condition.operator == "contains"
    assert condition.value == ""


@pytest.mark.parametrize(
    ("operator", "labels", "expected"),
    [
        ("contains", ["person", "car"], True),
        ("contains", ["car"], False),
        ("contains", [], False),
        ("not_contains", ["car"], True),
        ("not_contains", ["person"], False),
        ("not_contains", [], True),
    ],
)
def test_object_class_condition_matches(make_event, make_detection, operator, labels, expected):
    condition = ObjectClassCondition(operator=operator, value=" person ")
    event = make_event(detections=[make_detection(label=label) for label in labels])

    assert condition.matches(event) is expected


def test_object_class_match_is_exact(make_event, make_detection):
    condition = ObjectClassCondition(value="person")
    event = make_event(detections=[make_detection(label="Person"), make_detection(label="persons")])

    assert condition.matches(event) is False


@pytest.mark.parametrize("operator", ["contains", "not_contains"])
@pytest.mark.parametrize("value", ["", "   "])
def test_blank_object_class_never_matches(make_event, make_detection, operator, value):
    condition = ObjectClassCondition(operator=operator, value=value)
    event = make_event(detections=[make_detection()])

    assert condition.matches(event) is False
    assert condition.selected_class_label() is None


def test_object_class_condition_reports_stripped_label():
    condition = ObjectClassCondition(value="  person ")

    assert condition.selected_class_label() == "person"
    assert condition.selected_event_kind() is None


@pytest.mark.parametrize(
    "fields",
    [{"value": "x" * 257}, {"operator": "is"}, {"value": None}],
    ids=["long_value", "foreign_operator", "null_value"],
)
def test_object_class_condition_rejects_invalid_fields(fields):
    with pytest.raises(ValidationError):
        ObjectClassCondition(**fields)


def test_detection_count_defaults_to_at_least_one():
    condition = DetectionCountCondition()

    assert condition.field == "detection_count"
    assert condition.operator == "gte"
    assert condition.value == 1


@pytest.mark.parametrize(
    ("operator", "value", "count", "expected"),
    [
        ("gte", 1, 0, False),
        ("gte", 1, 1, True),
        ("eq", 2, 2, True),
        ("neq", 0, 0, False),
        ("lt", 2, 3, False),
        ("lte", 3, 3, True),
        ("gt", 0, 1, True),
    ],
)
def test_detection_count_compares_the_number_of_detections(
    make_event, make_detection, operator, value, count, expected
):
    condition = DetectionCountCondition(operator=operator, value=value)
    event = make_event(detections=[make_detection() for _ in range(count)])

    assert condition.matches(event) is expected


@pytest.mark.parametrize(
    "fields",
    [{"value": -1}, {"value": 1001}, {"value": 1.5}, {"operator": "is"}],
    ids=["negative", "above_limit", "fractional", "foreign_operator"],
)
def test_detection_count_rejects_invalid_fields(fields):
    with pytest.raises(ValidationError):
        DetectionCountCondition(**fields)


def test_max_confidence_defaults_to_at_least_half():
    condition = MaxConfidenceCondition()

    assert condition.field == "max_confidence"
    assert condition.operator == "gte"
    assert condition.value == 0.5


def test_max_confidence_uses_the_highest_detection(make_event, make_detection):
    condition = MaxConfidenceCondition(operator="gte", value=0.8)
    event = make_event(detections=[make_detection(confidence=0.3), make_detection(confidence=0.85)])

    assert condition.matches(event) is True


def test_max_confidence_below_threshold_does_not_match(make_event, make_detection):
    condition = MaxConfidenceCondition(operator="gte", value=0.9)
    event = make_event(detections=[make_detection(confidence=0.3), make_detection(confidence=0.85)])

    assert condition.matches(event) is False


def test_max_confidence_is_zero_without_detections(make_event):
    condition = MaxConfidenceCondition(operator="lte", value=0.0)

    assert condition.matches(make_event()) is True


@pytest.mark.parametrize("fields", [{"value": -0.1}, {"value": 1.1}, {"operator": "contains"}])
def test_max_confidence_rejects_invalid_fields(fields):
    with pytest.raises(ValidationError):
        MaxConfidenceCondition(**fields)


@pytest.mark.parametrize(
    ("field", "expected_type"),
    [
        ("event_kind", EventKindCondition),
        ("object_class", ObjectClassCondition),
        ("detection_count", DetectionCountCondition),
        ("max_confidence", MaxConfidenceCondition),
    ],
)
def test_condition_dispatches_on_field(field, expected_type):
    condition = condition_adapter.validate_python({"field": field})

    assert type(condition) is expected_type


@pytest.mark.parametrize(
    "payload",
    [
        {"field": "weather"},
        {},
        {"field": "event_kind", "value": "lower"},
        {"field": "object_class", "value": 3},
    ],
    ids=["unknown_field", "missing_field", "invalid_event_kind", "non_string_class"],
)
def test_condition_rejects_unknown_or_invalid_payload(payload):
    with pytest.raises(ValidationError):
        condition_adapter.validate_python(payload)


def test_runnable_event_kind_requires_a_value():
    with pytest.raises(ValidationError, match="value"):
        RunnableEventKindCondition()


def test_runnable_event_kind_rejects_explicit_null():
    with pytest.raises(ValidationError, match="value"):
        RunnableEventKindCondition(value=None)


@pytest.mark.parametrize("value", ["", "   "])
def test_runnable_object_class_requires_a_non_blank_value(value):
    with pytest.raises(ValidationError, match="value"):
        RunnableObjectClassCondition(value=value)


def test_runnable_object_class_strips_its_value():
    condition = RunnableObjectClassCondition(value=" person ")

    assert condition.value == "person"


@pytest.mark.parametrize(
    ("payload", "expected_type"),
    [
        ({"field": "event_kind", "value": "PERSON_DETECTED"}, RunnableEventKindCondition),
        ({"field": "object_class", "value": "person"}, RunnableObjectClassCondition),
        ({"field": "detection_count"}, DetectionCountCondition),
        ({"field": "max_confidence"}, MaxConfidenceCondition),
    ],
)
def test_runnable_condition_dispatches_on_field(payload, expected_type):
    condition = runnable_adapter.validate_python(payload)

    assert type(condition) is expected_type


@pytest.mark.parametrize(
    "draft",
    [EventKindCondition(), ObjectClassCondition(), ObjectClassCondition(value="  ")],
    ids=["unselected_event_kind", "blank_class", "whitespace_class"],
)
def test_runnable_condition_rejects_unconfigured_drafts(draft):
    with pytest.raises(ValidationError):
        runnable_adapter.validate_python(draft.model_dump())


def test_runnable_condition_accepts_configured_drafts():
    draft = EventKindCondition(operator="is_not", value="CAR_DETECTED")

    condition = runnable_adapter.validate_python(draft.model_dump())

    assert condition == RunnableEventKindCondition(operator="is_not", value="CAR_DETECTED")
