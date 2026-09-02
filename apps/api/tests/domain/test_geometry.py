"""Pure geometry over normalized frame coordinates."""

import pytest

from api.domain.geometry import normalized_box_center, point_in_polygon

UNIT_SQUARE = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
TRIANGLE = [(0.0, 0.0), (1.0, 0.0), (0.5, 1.0)]
# Unit square with a notch cut in from the left edge between y=0.3 and y=0.7.
C_SHAPE = [
    (0.0, 0.0),
    (1.0, 0.0),
    (1.0, 1.0),
    (0.0, 1.0),
    (0.0, 0.7),
    (0.7, 0.7),
    (0.7, 0.3),
    (0.0, 0.3),
]


@pytest.mark.parametrize(
    ("box", "frame", "expected"),
    [
        ((0.0, 0.0, 100.0, 50.0), (200, 100), (0.25, 0.25)),
        ((50.0, 50.0, 150.0, 150.0), (200, 200), (0.5, 0.5)),
        ((0.0, 0.0, 0.0, 0.0), (640, 480), (0.0, 0.0)),
        ((640.0, 480.0, 640.0, 480.0), (640, 480), (1.0, 1.0)),
        ((100.0, 0.0, 300.0, 480.0), (400, 480), (0.5, 0.5)),
    ],
    ids=["top_left_quarter", "centered", "origin_point", "far_corner", "tall_box"],
)
def test_box_center_is_normalized_by_frame_size(box, frame, expected):
    width, height = frame

    center = normalized_box_center(box, width, height)

    assert center == pytest.approx(expected)


def test_box_center_can_leave_the_frame():
    center = normalized_box_center((900.0, 900.0, 1100.0, 1100.0), 1000, 1000)

    assert center == pytest.approx((1.0, 1.0))


@pytest.mark.parametrize("point", [(0.5, 0.5), (0.01, 0.99), (0.99, 0.01)])
def test_point_inside_square(point):
    assert point_in_polygon(point, UNIT_SQUARE) is True


@pytest.mark.parametrize("point", [(1.5, 0.5), (-0.1, 0.5), (0.5, 1.2), (0.5, -0.1)])
def test_point_outside_square(point):
    assert point_in_polygon(point, UNIT_SQUARE) is False


@pytest.mark.parametrize(
    ("point", "expected"),
    [
        ((0.0, 0.5), True),
        ((0.5, 0.0), True),
        ((0.0, 0.0), True),
        ((1.0, 0.5), False),
        ((0.5, 1.0), False),
        ((1.0, 1.0), False),
    ],
    ids=["left_edge", "bottom_edge", "origin_vertex", "right_edge", "top_edge", "far_vertex"],
)
def test_boundary_is_half_open(point, expected):
    assert point_in_polygon(point, UNIT_SQUARE) is expected


@pytest.mark.parametrize(
    ("point", "expected"),
    [
        ((0.5, 0.4), True),
        ((0.5, 0.99), True),
        ((0.1, 0.9), False),
        ((0.9, 0.9), False),
        ((0.5, 1.5), False),
    ],
    ids=["centre", "near_apex", "left_of_slope", "right_of_slope", "above_apex"],
)
def test_triangle_membership(point, expected):
    assert point_in_polygon(point, TRIANGLE) is expected


@pytest.mark.parametrize(
    ("point", "expected"),
    [
        ((0.3, 0.5), False),
        ((0.85, 0.5), True),
        ((0.3, 0.15), True),
        ((0.3, 0.85), True),
    ],
    ids=["in_notch", "spine", "lower_arm", "upper_arm"],
)
def test_concave_polygon_excludes_its_notch(point, expected):
    assert point_in_polygon(point, C_SHAPE) is expected


@pytest.mark.parametrize("point", [(0.3, 0.5), (0.85, 0.5), (0.3, 0.15), (0.0, 0.5), (1.0, 0.5)])
def test_winding_order_does_not_change_membership(point):
    clockwise = list(reversed(C_SHAPE))

    assert point_in_polygon(point, clockwise) is point_in_polygon(point, C_SHAPE)


@pytest.mark.parametrize("polygon", [[], [(0.0, 0.0)], [(0.0, 0.0), (1.0, 1.0)]])
def test_degenerate_polygon_contains_nothing(polygon):
    assert point_in_polygon((0.5, 0.5), polygon) is False


def test_accepts_tuple_polygons():
    assert point_in_polygon((0.5, 0.5), tuple(UNIT_SQUARE)) is True
