"""Filter node payloads; each filter owns its pass/fail semantics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal, Self

from pydantic import Field, model_validator

from api.domain.geometry import normalized_box_center, point_in_polygon
from api.domain.workflow.base import ClassLabel, NormalizedPoint, Weekday, WorkflowModel
from api.domain.workflow.conditions import (
    EventKindCondition,
    IfElseCondition,
    RunnableIfElseCondition,
)

if TYPE_CHECKING:
    from api.domain.events import DetectionEvent
    from api.domain.geometry import Point
    from api.domain.workflow.runtime import FilterRuntime
    from shared import Detection


def _detection_center(event: DetectionEvent, detection: Detection) -> Point:
    return normalized_box_center(detection.bounding_box, event.frame_width, event.frame_height)


class FilterNodeData(WorkflowModel):
    """Base contract for filter payloads: route one event to the if or else branch.

    Commercial filters registered through api.domain.workflow.extensions subclass
    this too, so runtime dispatch must check this base, not the FilterData union.
    """

    def passes(self, event: DetectionEvent, runtime: FilterRuntime) -> bool:
        raise NotImplementedError


class IfElseFilterData(FilterNodeData):
    kind: Literal["if_else_filter"] = "if_else_filter"
    condition: IfElseCondition = Field(default_factory=EventKindCondition)

    def passes(self, event: DetectionEvent, runtime: FilterRuntime) -> bool:
        return self.condition.matches(event)


class ZoneFilterData(FilterNodeData):
    kind: Literal["zone_filter"] = "zone_filter"
    polygon: list[NormalizedPoint] = Field(default_factory=list, max_length=100)

    def passes(self, event: DetectionEvent, runtime: FilterRuntime) -> bool:
        if len(self.polygon) < 3 or not event.detections:
            return True

        return any(
            point_in_polygon(_detection_center(event, detection), self.polygon)
            for detection in event.detections
        )


class ClassFilterData(FilterNodeData):
    kind: Literal["class_filter"] = "class_filter"
    classes: list[ClassLabel] = Field(default_factory=list, max_length=64)

    def passes(self, event: DetectionEvent, runtime: FilterRuntime) -> bool:
        if not self.classes:
            return True

        labels = {detection.label for detection in event.detections}

        return bool(labels.intersection(self.classes))


class DebounceFilterData(FilterNodeData):
    kind: Literal["debounce_filter"] = "debounce_filter"
    seconds: int = Field(default=30, ge=1, le=3600)

    def passes(self, event: DetectionEvent, runtime: FilterRuntime) -> bool:
        return runtime.state.debounce_allows(
            runtime.workflow_id,
            runtime.run_id,
            runtime.node_id,
            event.camera_id,
            self.seconds,
        )


class TimeWindowFilterData(FilterNodeData):
    """Pass inside the configured window; invert=True passes outside it (after-hours)."""

    kind: Literal["time_window_filter"] = "time_window_filter"
    start_hour: int = Field(default=0, ge=0, le=23)
    end_hour: int = Field(default=23, ge=0, le=23)
    weekdays: list[Weekday] = Field(default_factory=lambda: [0, 1, 2, 3, 4], max_length=7)
    invert: bool = False

    def passes(self, event: DetectionEvent, runtime: FilterRuntime) -> bool:
        local = event.ts.astimezone(runtime.timezone)
        hour = local.hour

        if self.start_hour <= self.end_hour:
            in_hours = self.start_hour <= hour <= self.end_hour
        else:
            in_hours = hour >= self.start_hour or hour <= self.end_hour

        inside = local.weekday() in self.weekdays and in_hours

        return inside != self.invert


class SizeFilterData(FilterNodeData):
    """Pass when any detection's bbox area (as a fraction of the frame) is within bounds."""

    kind: Literal["size_filter"] = "size_filter"
    min_area: float = Field(default=0.0, ge=0.0, le=1.0)
    max_area: float = Field(default=1.0, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_area_range(self) -> Self:
        if self.min_area > self.max_area:
            raise ValueError("min_area must not exceed max_area")

        return self

    def passes(self, event: DetectionEvent, runtime: FilterRuntime) -> bool:
        if not event.detections:
            return True

        frame_area = float(event.frame_width * event.frame_height)

        for detection in event.detections:
            x_min, y_min, x_max, y_max = detection.bounding_box
            area = max(0.0, x_max - x_min) * max(0.0, y_max - y_min) / frame_area

            if self.min_area <= area <= self.max_area:
                return True

        return False


FilterData = (
    IfElseFilterData
    | ZoneFilterData
    | ClassFilterData
    | DebounceFilterData
    | TimeWindowFilterData
    | SizeFilterData
)


RunnablePolygon = Annotated[list[NormalizedPoint], Field(min_length=3, max_length=100)]


class RunnableIfElseFilter(IfElseFilterData):
    condition: RunnableIfElseCondition


class RunnableZoneFilter(ZoneFilterData):
    polygon: RunnablePolygon


class RunnableTimeWindowFilter(TimeWindowFilterData):
    weekdays: list[Weekday] = Field(min_length=1, max_length=7)
