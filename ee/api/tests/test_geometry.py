"""Line-crossing geometry over normalized coordinates."""

import pytest

from ee.workflow.geometry import line_crossing_matches, segments_intersect, signed_side

HORIZONTAL = ((0.0, 0.5), (1.0, 0.5))


def test_signed_side_separates_the_two_half_planes():
    below = signed_side(*HORIZONTAL, (0.5, 0.2))
    above = signed_side(*HORIZONTAL, (0.5, 0.8))
    on_line = signed_side(*HORIZONTAL, (0.3, 0.5))

    assert below < 0 < above
    assert on_line == 0


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    [
        (((0.5, 0.2), (0.5, 0.8)), HORIZONTAL, True),
        (((0.2, 0.2), (0.8, 0.8)), ((0.2, 0.8), (0.8, 0.2)), True),
        (((0.5, 0.6), (0.5, 0.9)), HORIZONTAL, False),
        (((0.0, 0.1), (1.0, 0.1)), HORIZONTAL, False),
        (((0.0, 0.5), (0.4, 0.5)), ((0.6, 0.5), (1.0, 0.5)), False),
    ],
)
def test_segments_intersect_only_when_they_cross(first, second, expected):
    assert segments_intersect(*first, *second) is expected


@pytest.mark.parametrize(
    ("previous", "current", "direction", "expected"),
    [
        ((0.5, 0.8), (0.5, 0.2), "any", True),
        ((0.5, 0.8), (0.5, 0.2), "in", True),
        ((0.5, 0.8), (0.5, 0.2), "out", False),
        ((0.5, 0.2), (0.5, 0.8), "in", False),
        ((0.5, 0.2), (0.5, 0.8), "out", True),
        ((0.5, 0.6), (0.5, 0.9), "any", False),
        ((0.5, 0.6), (0.5, 0.9), "in", False),
    ],
)
def test_line_crossing_respects_direction(previous, current, direction, expected):
    assert line_crossing_matches(previous, current, *HORIZONTAL, direction) is expected
