"""Measurement filter payloads; each filter owns its pass/fail semantics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import Field

from api.domain.geometry import normalized_box_center, point_in_polygon
from api.domain.workflow.base import NormalizedPoint
from api.domain.workflow.filters import FilterNodeData, RunnablePolygon
from ee.workflow.geometry import CrossingDirection, line_crossing_matches

if TYPE_CHECKING:
    from api.domain.events import DetectionEvent
    from api.domain.geometry import Point
    from api.domain.workflow.runtime import FilterRuntime
    from shared import Detection


def _detection_center(event: DetectionEvent, detection: Detection) -> Point:
    return normalized_box_center(detection.bounding_box, event.frame_width, event.frame_height)


class LineCrossingFilterData(FilterNodeData):
    """Pass when a tracked object crosses the line (2 normalized points) this frame.

    Direction is relative to the line's drawing order p1→p2: "in" means crossing
    from its left side to its right side, "out" the reverse, "any" either way.
    """

    kind: Literal["line_crossing_filter"] = "line_crossing_filter"
    line: list[NormalizedPoint] = Field(default_factory=list, max_length=2)
    direction: CrossingDirection = "any"

    def passes(self, event: DetectionEvent, runtime: FilterRuntime) -> bool:
        if len(self.line) != 2:
            return True

        line_start, line_end = self.line
        crossed = False

        for detection in event.detections:
            if detection.tracker_id is None:
                continue

            current = _detection_center(event, detection)
            previous = runtime.state.swap_track_point(
                runtime.workflow_id,
                runtime.run_id,
                runtime.node_id,
                event.camera_id,
                detection.tracker_id,
                current,
                event.ts,
            )

            if crossed or previous is None:
                continue

            crossed = line_crossing_matches(previous, current, line_start, line_end, self.direction)

        return crossed


class DwellFilterData(FilterNodeData):
    kind: Literal["dwell_filter"] = "dwell_filter"
    polygon: list[NormalizedPoint] = Field(default_factory=list, max_length=100)
    min_seconds: int = Field(default=60, ge=1, le=3600)

    def passes(self, event: DetectionEvent, runtime: FilterRuntime) -> bool:
        if len(self.polygon) < 3:
            return True

        dwelled = False

        for detection in event.detections:
            if detection.tracker_id is None:
                continue

            inside = point_in_polygon(_detection_center(event, detection), self.polygon)
            elapsed = runtime.state.dwell_seconds(
                runtime.workflow_id,
                runtime.run_id,
                runtime.node_id,
                event.camera_id,
                detection.tracker_id,
                inside,
                event.ts,
            )

            if elapsed >= self.min_seconds:
                dwelled = True

        return dwelled


class CountThresholdFilterData(FilterNodeData):
    kind: Literal["count_threshold_filter"] = "count_threshold_filter"
    polygon: list[NormalizedPoint] = Field(default_factory=list, max_length=100)
    operator: Literal["gte", "lte"] = "gte"
    count: int = Field(default=1, ge=0, le=1000)

    def passes(self, event: DetectionEvent, runtime: FilterRuntime) -> bool:
        if len(self.polygon) >= 3:
            matched = sum(
                point_in_polygon(_detection_center(event, detection), self.polygon)
                for detection in event.detections
            )
        else:
            matched = len(event.detections)

        return matched >= self.count if self.operator == "gte" else matched <= self.count


class RunnableLineCrossingFilter(LineCrossingFilterData):
    line: tuple[NormalizedPoint, NormalizedPoint]


class RunnableDwellFilter(DwellFilterData):
    polygon: RunnablePolygon
