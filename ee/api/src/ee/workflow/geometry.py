"""Line-crossing geometry over normalized frame coordinates."""

from typing import Literal

from api.domain.geometry import Point

type CrossingDirection = Literal["any", "in", "out"]


def signed_side(line_start: Point, line_end: Point, point: Point) -> float:
    return (line_end[0] - line_start[0]) * (point[1] - line_start[1]) - (
        line_end[1] - line_start[1]
    ) * (point[0] - line_start[0])


def segments_intersect(
    first_start: Point, first_end: Point, second_start: Point, second_end: Point
) -> bool:
    first_side_start = signed_side(second_start, second_end, first_start)
    first_side_end = signed_side(second_start, second_end, first_end)
    second_side_start = signed_side(first_start, first_end, second_start)
    second_side_end = signed_side(first_start, first_end, second_end)

    return ((first_side_start > 0) != (first_side_end > 0)) and (
        (second_side_start > 0) != (second_side_end > 0)
    )


def line_crossing_matches(
    previous: Point,
    current: Point,
    line_start: Point,
    line_end: Point,
    direction: CrossingDirection,
) -> bool:
    if not segments_intersect(previous, current, line_start, line_end):
        return False
    if direction == "any":
        return True

    crossed_in = (
        signed_side(line_start, line_end, previous)
        > 0
        >= signed_side(line_start, line_end, current)
    )

    return crossed_in if direction == "in" else not crossed_in
