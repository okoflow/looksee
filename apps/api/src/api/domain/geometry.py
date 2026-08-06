"""Pure 2D geometry over normalized frame coordinates."""

from collections.abc import Sequence

type Point = tuple[float, float]
type BoundingBox = tuple[float, float, float, float]


def normalized_box_center(box: BoundingBox, frame_width: int, frame_height: int) -> Point:
    x_min, y_min, x_max, y_max = box

    return (
        (x_min + x_max) / 2.0 / frame_width,
        (y_min + y_max) / 2.0 / frame_height,
    )


def point_in_polygon(point: Point, polygon: Sequence[Point]) -> bool:
    if len(polygon) < 3:
        return False

    px, py = point
    inside = False
    previous_index = len(polygon) - 1

    for index, (x_current, y_current) in enumerate(polygon):
        x_previous, y_previous = polygon[previous_index]
        intersects = ((y_current > py) != (y_previous > py)) and (
            px
            < (x_previous - x_current) * (py - y_current) / (y_previous - y_current + 1e-12)
            + x_current
        )
        if intersects:
            inside = not inside
        previous_index = index

    return inside
