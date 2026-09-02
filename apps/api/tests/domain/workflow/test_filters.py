"""Filter payloads: field bounds and pass/fail semantics."""

import typing
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from api.domain.workflow.conditions import EventKindCondition
from api.domain.workflow.filters import (
    ClassFilterData,
    DebounceFilterData,
    FilterData,
    FilterNodeData,
    IfElseFilterData,
    RunnableIfElseFilter,
    RunnableTimeWindowFilter,
    RunnableZoneFilter,
    SizeFilterData,
    TimeWindowFilterData,
    ZoneFilterData,
)

CENTRAL_SQUARE = [(0.25, 0.25), (0.75, 0.25), (0.75, 0.75), (0.25, 0.75)]
CENTERED_BOX = (400.0, 400.0, 600.0, 600.0)
CORNER_BOX = (0.0, 0.0, 100.0, 100.0)


def wednesday_at(hour, minute=0):
    return datetime(2026, 1, 7, hour, minute, tzinfo=UTC)


def test_base_filter_has_no_semantics(make_event, make_runtime):
    with pytest.raises(NotImplementedError):
        FilterNodeData().passes(make_event(), make_runtime())


def test_every_filter_extends_the_base():
    for filter_type in typing.get_args(FilterData):
        assert issubclass(filter_type, FilterNodeData)


def test_filter_union_kinds():
    kinds = {
        filter_type.model_fields["kind"].default for filter_type in typing.get_args(FilterData)
    }

    expected = {
        "if_else_filter",
        "zone_filter",
        "class_filter",
        "debounce_filter",
        "time_window_filter",
        "size_filter",
    }

    assert kinds == expected


def test_if_else_defaults_to_an_unselected_event_kind():
    data = IfElseFilterData()

    assert data.kind == "if_else_filter"
    assert data.condition == EventKindCondition()


def test_if_else_never_passes_while_unconfigured(make_event, make_runtime):
    data = IfElseFilterData()

    assert data.passes(make_event(), make_runtime()) is False


def test_if_else_delegates_to_its_condition(make_event, make_detection, make_runtime):
    data = IfElseFilterData(condition={"field": "detection_count", "operator": "gte", "value": 2})
    one = make_event(detections=[make_detection()])
    two = make_event(detections=[make_detection(), make_detection()])
    runtime = make_runtime()

    assert data.passes(one, runtime) is False
    assert data.passes(two, runtime) is True


def test_if_else_rejects_unknown_condition_field():
    with pytest.raises(ValidationError):
        IfElseFilterData(condition={"field": "weather"})


def test_zone_defaults_to_no_polygon():
    data = ZoneFilterData()

    assert data.kind == "zone_filter"
    assert data.polygon == []


def test_zone_passes_when_any_detection_center_is_inside(make_event, make_detection, make_runtime):
    data = ZoneFilterData(polygon=CENTRAL_SQUARE)
    outside = make_detection(bounding_box=CORNER_BOX)
    inside = make_detection(bounding_box=CENTERED_BOX)
    event = make_event(detections=[outside, inside])

    assert data.passes(event, make_runtime()) is True


def test_zone_fails_when_every_center_is_outside(make_event, make_detection, make_runtime):
    data = ZoneFilterData(polygon=CENTRAL_SQUARE)
    event = make_event(detections=[make_detection(bounding_box=CORNER_BOX)])

    assert data.passes(event, make_runtime()) is False


def test_zone_judges_the_center_not_the_corners(make_event, make_detection, make_runtime):
    data = ZoneFilterData(polygon=CENTRAL_SQUARE)
    straddling = make_detection(bounding_box=(0.0, 0.0, 1000.0, 1000.0))
    event = make_event(detections=[straddling])

    assert data.passes(event, make_runtime()) is True


def test_zone_normalizes_centers_by_frame_size(make_event, make_detection, make_runtime):
    data = ZoneFilterData(polygon=CENTRAL_SQUARE)
    detection = make_detection(bounding_box=CENTERED_BOX)
    wide_frame = make_event(frame_width=4000, frame_height=1000, detections=[detection])
    square_frame = make_event(frame_width=1000, frame_height=1000, detections=[detection])
    runtime = make_runtime()

    assert data.passes(wide_frame, runtime) is False
    assert data.passes(square_frame, runtime) is True


@pytest.mark.parametrize("polygon", [[], [(0.0, 0.0), (1.0, 1.0)]], ids=["empty", "two_points"])
def test_zone_without_a_polygon_passes_everything(
    make_event, make_detection, make_runtime, polygon
):
    data = ZoneFilterData(polygon=polygon)
    event = make_event(detections=[make_detection(bounding_box=CORNER_BOX)])

    assert data.passes(event, make_runtime()) is True


def test_zone_passes_events_without_detections(make_event, make_runtime):
    data = ZoneFilterData(polygon=CENTRAL_SQUARE)

    assert data.passes(make_event(), make_runtime()) is True


@pytest.mark.parametrize(
    "polygon",
    [
        [(1.5, 0.0), (0.0, 0.0), (1.0, 1.0)],
        [(-0.1, 0.0), (0.0, 0.0), (1.0, 1.0)],
        [(0.0, 0.0, 0.0), (0.0, 0.0), (1.0, 1.0)],
        [(0.0,), (0.0, 0.0), (1.0, 1.0)],
        [(0.0, 0.0)] * 101,
    ],
    ids=["x_above_one", "x_negative", "three_dimensions", "one_dimension", "too_many_points"],
)
def test_zone_rejects_invalid_polygon(polygon):
    with pytest.raises(ValidationError, match="polygon"):
        ZoneFilterData(polygon=polygon)


def test_class_filter_defaults_to_no_classes():
    data = ClassFilterData()

    assert data.kind == "class_filter"
    assert data.classes == []


@pytest.mark.parametrize(
    ("classes", "labels", "expected"),
    [
        ([], ["dog"], True),
        ([], [], True),
        (["person"], ["person"], True),
        (["person", "car"], ["dog", "car"], True),
        (["person"], ["dog"], False),
        (["person"], [], False),
        (["person"], ["Person"], False),
    ],
    ids=[
        "unfiltered",
        "unfiltered_empty",
        "exact",
        "partial_overlap",
        "no_overlap",
        "no_detections",
        "case_sensitive",
    ],
)
def test_class_filter_passes_on_label_overlap(
    make_event, make_detection, make_runtime, classes, labels, expected
):
    data = ClassFilterData(classes=classes)
    event = make_event(detections=[make_detection(label=label) for label in labels])

    assert data.passes(event, make_runtime()) is expected


@pytest.mark.parametrize(
    "classes",
    [[""], ["x" * 129], ["a"] * 65],
    ids=["empty_label", "long_label", "too_many"],
)
def test_class_filter_rejects_invalid_labels(classes):
    with pytest.raises(ValidationError, match="classes"):
        ClassFilterData(classes=classes)


def test_debounce_defaults_to_thirty_seconds():
    data = DebounceFilterData()

    assert data.kind == "debounce_filter"
    assert data.seconds == 30


@pytest.mark.parametrize("seconds", [1, 3600])
def test_debounce_accepts_boundary_seconds(seconds):
    data = DebounceFilterData(seconds=seconds)

    assert data.seconds == seconds


@pytest.mark.parametrize("seconds", [0, 3601, 1.5])
def test_debounce_rejects_out_of_range_seconds(seconds):
    with pytest.raises(ValidationError, match="seconds"):
        DebounceFilterData(seconds=seconds)


@pytest.mark.parametrize("allowed", [True, False])
def test_debounce_defers_to_runtime_state(make_event, make_state, make_runtime, allowed):
    data = DebounceFilterData(seconds=45)
    state = make_state(debounce=allowed)
    runtime = make_runtime(state=state, node_id="debounce-1")
    event = make_event()

    result = data.passes(event, runtime)

    expected_call = (
        "debounce_allows",
        runtime.workflow_id,
        runtime.run_id,
        "debounce-1",
        event.camera_id,
        45,
    )

    assert result is allowed
    assert state.calls == [expected_call]


def test_time_window_defaults_to_weekdays_all_day():
    data = TimeWindowFilterData()

    assert data.kind == "time_window_filter"
    assert data.start_hour == 0
    assert data.end_hour == 23
    assert data.weekdays == [0, 1, 2, 3, 4]
    assert data.invert is False


@pytest.mark.parametrize(
    ("hour", "expected"),
    [(8, False), (9, True), (12, True), (17, True), (18, False)],
)
def test_time_window_hours_are_inclusive(make_event, make_runtime, hour, expected):
    data = TimeWindowFilterData(start_hour=9, end_hour=17)
    event = make_event(ts=wednesday_at(hour, 30))

    assert data.passes(event, make_runtime()) is expected


@pytest.mark.parametrize(
    ("hour", "expected"),
    [(21, False), (22, True), (23, True), (0, True), (6, True), (7, False), (12, False)],
)
def test_time_window_wraps_past_midnight(make_event, make_runtime, hour, expected):
    data = TimeWindowFilterData(start_hour=22, end_hour=6, weekdays=list(range(7)))
    event = make_event(ts=wednesday_at(hour))

    assert data.passes(event, make_runtime()) is expected


def test_time_window_single_hour(make_event, make_runtime):
    data = TimeWindowFilterData(start_hour=12, end_hour=12)
    runtime = make_runtime()

    assert data.passes(make_event(ts=wednesday_at(12, 59)), runtime) is True
    assert data.passes(make_event(ts=wednesday_at(13)), runtime) is False


def test_time_window_rejects_days_outside_the_selection(make_event, make_runtime):
    data = TimeWindowFilterData(weekdays=[5, 6])
    wednesday = make_event(ts=wednesday_at(12))
    saturday = make_event(ts=datetime(2026, 1, 10, 12, tzinfo=UTC))
    runtime = make_runtime()

    assert data.passes(wednesday, runtime) is False
    assert data.passes(saturday, runtime) is True


def test_time_window_invert_passes_outside_the_window(make_event, make_runtime):
    data = TimeWindowFilterData(start_hour=9, end_hour=17, invert=True)
    inside = make_event(ts=wednesday_at(12))
    outside = make_event(ts=wednesday_at(20))
    runtime = make_runtime()

    assert data.passes(inside, runtime) is False
    assert data.passes(outside, runtime) is True


def test_time_window_invert_treats_unselected_days_as_outside(make_event, make_runtime):
    data = TimeWindowFilterData(weekdays=[5, 6], invert=True)
    wednesday = make_event(ts=wednesday_at(12))

    assert data.passes(wednesday, make_runtime()) is True


def test_time_window_evaluates_in_the_runtime_timezone(make_event, make_runtime):
    data = TimeWindowFilterData(start_hour=9, end_hour=17, weekdays=list(range(7)))
    event = make_event(ts=wednesday_at(15))

    assert data.passes(event, make_runtime(timezone="America/New_York")) is True
    assert data.passes(event, make_runtime(timezone="Asia/Tokyo")) is False


def test_time_window_timezone_can_shift_the_weekday(make_event, make_runtime):
    data = TimeWindowFilterData(weekdays=[3])
    late_wednesday_utc = make_event(ts=wednesday_at(23))

    assert data.passes(late_wednesday_utc, make_runtime(timezone="UTC")) is False
    assert data.passes(late_wednesday_utc, make_runtime(timezone="Asia/Tokyo")) is True


def test_time_window_honours_the_event_offset(make_event, make_runtime):
    data = TimeWindowFilterData(start_hour=9, end_hour=17, weekdays=list(range(7)))
    event = make_event(ts=datetime.fromisoformat("2026-01-07T12:00:00+09:00"))

    assert data.passes(event, make_runtime(timezone="Asia/Tokyo")) is True
    assert data.passes(event, make_runtime(timezone="UTC")) is False


@pytest.mark.parametrize(
    "fields",
    [
        {"start_hour": -1},
        {"start_hour": 24},
        {"end_hour": -1},
        {"end_hour": 24},
        {"weekdays": [7]},
        {"weekdays": [-1]},
        {"weekdays": [0] * 8},
        {"invert": "yes please"},
    ],
    ids=[
        "start_negative",
        "start_24",
        "end_negative",
        "end_24",
        "day_seven",
        "day_negative",
        "too_many_days",
        "non_bool_invert",
    ],
)
def test_time_window_rejects_out_of_range_fields(fields):
    with pytest.raises(ValidationError):
        TimeWindowFilterData(**fields)


def test_size_defaults_to_the_full_range():
    data = SizeFilterData()

    assert data.kind == "size_filter"
    assert data.min_area == 0.0
    assert data.max_area == 1.0


def test_size_rejects_an_inverted_range():
    with pytest.raises(ValidationError, match="min_area must not exceed max_area"):
        SizeFilterData(min_area=0.6, max_area=0.4)


def test_size_accepts_an_empty_range():
    data = SizeFilterData(min_area=0.5, max_area=0.5)

    assert data.min_area == data.max_area


@pytest.mark.parametrize(
    "fields",
    [{"min_area": -0.1}, {"max_area": 1.1}, {"min_area": 1.1, "max_area": 1.2}],
    ids=["min_negative", "max_above_one", "both_above_one"],
)
def test_size_rejects_out_of_range_area(fields):
    with pytest.raises(ValidationError):
        SizeFilterData(**fields)


@pytest.mark.parametrize(
    ("box", "expected"),
    [
        ((0.0, 0.0, 100.0, 100.0), True),
        ((0.0, 0.0, 500.0, 500.0), True),
        ((0.0, 0.0, 50.0, 50.0), False),
        ((0.0, 0.0, 600.0, 600.0), False),
    ],
    ids=["at_min", "at_max", "too_small", "too_large"],
)
def test_size_bounds_are_inclusive(make_event, make_detection, make_runtime, box, expected):
    data = SizeFilterData(min_area=0.01, max_area=0.25)
    event = make_event(detections=[make_detection(bounding_box=box)])

    assert data.passes(event, make_runtime()) is expected


def test_size_passes_when_any_detection_fits(make_event, make_detection, make_runtime):
    data = SizeFilterData(min_area=0.01, max_area=0.25)
    too_small = make_detection(bounding_box=(0.0, 0.0, 10.0, 10.0))
    fitting = make_detection(bounding_box=(0.0, 0.0, 200.0, 200.0))
    event = make_event(detections=[too_small, fitting])

    assert data.passes(event, make_runtime()) is True


def test_size_passes_events_without_detections(make_event, make_runtime):
    data = SizeFilterData(min_area=0.5, max_area=0.6)

    assert data.passes(make_event(), make_runtime()) is True


def test_size_measures_area_relative_to_the_frame(make_event, make_detection, make_runtime):
    data = SizeFilterData(min_area=0.5)
    detection = make_detection(bounding_box=(0.0, 0.0, 500.0, 500.0))
    large_frame = make_event(detections=[detection])
    small_frame = make_event(frame_width=500, frame_height=500, detections=[detection])
    runtime = make_runtime()

    assert data.passes(large_frame, runtime) is False
    assert data.passes(small_frame, runtime) is True


def test_size_treats_a_degenerate_box_as_zero_area(make_event, make_detection, make_runtime):
    data = SizeFilterData(min_area=0.0, max_area=0.0)
    event = make_event(detections=[make_detection(bounding_box=(10.0, 10.0, 10.0, 10.0))])

    assert data.passes(event, make_runtime()) is True


def test_runnable_zone_requires_three_points():
    with pytest.raises(ValidationError, match="polygon"):
        RunnableZoneFilter(polygon=[(0.0, 0.0), (1.0, 1.0)])


def test_runnable_zone_accepts_a_triangle():
    runnable = RunnableZoneFilter(polygon=[(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)])

    assert len(runnable.polygon) == 3


def test_runnable_time_window_requires_a_weekday():
    with pytest.raises(ValidationError, match="weekdays"):
        RunnableTimeWindowFilter(weekdays=[])


def test_runnable_time_window_has_no_weekday_default_of_its_own():
    with pytest.raises(ValidationError, match="weekdays"):
        RunnableTimeWindowFilter()


def test_runnable_time_window_accepts_the_draft_default_weekdays():
    draft = TimeWindowFilterData()

    runnable = RunnableTimeWindowFilter.model_validate(draft.model_dump())

    assert runnable.weekdays == [0, 1, 2, 3, 4]


def test_runnable_if_else_requires_a_condition():
    with pytest.raises(ValidationError, match="condition"):
        RunnableIfElseFilter()


def test_runnable_if_else_requires_a_selected_event_kind():
    with pytest.raises(ValidationError, match="value"):
        RunnableIfElseFilter(condition={"field": "event_kind"})


def test_runnable_if_else_accepts_a_configured_condition():
    runnable = RunnableIfElseFilter(condition={"field": "event_kind", "value": "PERSON_DETECTED"})

    assert runnable.condition.value == "PERSON_DETECTED"
