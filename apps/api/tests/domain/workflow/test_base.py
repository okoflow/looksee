"""WorkflowModel configuration and shared value constraints."""

import math

import pytest
from pydantic import TypeAdapter, ValidationError

from api.domain.workflow.base import (
    ClassLabel,
    NormalizedCoordinate,
    NormalizedPoint,
    Weekday,
    WorkflowModel,
)


class Sample(WorkflowModel):
    value: float = 0.0


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError, match="Extra inputs"):
        Sample(unexpected=1)


@pytest.mark.parametrize("value", [math.inf, -math.inf, math.nan])
def test_non_finite_numbers_are_rejected(value):
    with pytest.raises(ValidationError):
        Sample(value=value)


def test_finite_numbers_are_kept():
    sample = Sample(value=1.5)

    assert sample.value == 1.5


@pytest.mark.parametrize(
    ("annotation", "value"),
    [
        (NormalizedCoordinate, 0.0),
        (NormalizedCoordinate, 0.5),
        (NormalizedCoordinate, 1.0),
        (NormalizedPoint, (0.0, 1.0)),
        (Weekday, 0),
        (Weekday, 6),
        (ClassLabel, "a"),
        (ClassLabel, "x" * 128),
    ],
    ids=[
        "coordinate_zero",
        "coordinate_half",
        "coordinate_one",
        "point_corner",
        "monday",
        "sunday",
        "shortest_label",
        "longest_label",
    ],
)
def test_value_types_accept_boundaries(annotation, value):
    validated = TypeAdapter(annotation).validate_python(value)

    assert validated == value


@pytest.mark.parametrize(
    ("annotation", "value"),
    [
        (NormalizedCoordinate, -0.01),
        (NormalizedCoordinate, 1.01),
        (NormalizedPoint, (0.0, 1.5)),
        (NormalizedPoint, (0.5,)),
        (NormalizedPoint, (0.5, 0.5, 0.5)),
        (Weekday, -1),
        (Weekday, 7),
        (ClassLabel, ""),
        (ClassLabel, "x" * 129),
    ],
    ids=[
        "coordinate_negative",
        "coordinate_above_one",
        "point_out_of_range",
        "point_one_dimension",
        "point_three_dimensions",
        "day_negative",
        "day_seven",
        "empty_label",
        "long_label",
    ],
)
def test_value_types_reject_out_of_range(annotation, value):
    with pytest.raises(ValidationError):
        TypeAdapter(annotation).validate_python(value)
