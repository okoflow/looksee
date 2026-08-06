"""If/else condition payloads; each condition owns its match semantics."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Literal, assert_never

from pydantic import Field, StringConstraints

from api.domain.workflow.base import WorkflowModel
from shared import EventKind

if TYPE_CHECKING:
    from api.domain.events import DetectionEvent

NumericComparisonOperator = Literal["eq", "neq", "gt", "gte", "lt", "lte"]


def compare_number(left: float, operator: NumericComparisonOperator, right: float) -> bool:
    if operator == "eq":
        return left == right
    if operator == "neq":
        return left != right
    if operator == "gt":
        return left > right
    if operator == "gte":
        return left >= right
    if operator == "lt":
        return left < right
    if operator == "lte":
        return left <= right
    assert_never(operator)


class ConditionModel(WorkflowModel):
    """Common capability-introspection surface for upstream-compatibility checks."""

    def selected_event_kind(self) -> EventKind | None:
        return None

    def selected_class_label(self) -> str | None:
        return None


class EventKindCondition(ConditionModel):
    field: Literal["event_kind"] = "event_kind"
    operator: Literal["is", "is_not"] = "is"
    value: EventKind | None = None

    def matches(self, event: DetectionEvent) -> bool:
        if self.value is None:
            return False

        is_selected = event.kind == self.value

        return is_selected if self.operator == "is" else not is_selected

    def selected_event_kind(self) -> EventKind | None:
        return self.value


class ObjectClassCondition(ConditionModel):
    field: Literal["object_class"] = "object_class"
    operator: Literal["contains", "not_contains"] = "contains"
    value: str = Field(default="", max_length=256)

    def matches(self, event: DetectionEvent) -> bool:
        label = self.value.strip()
        if not label:
            return False

        found = any(detection.label == label for detection in event.detections)

        return found if self.operator == "contains" else not found

    def selected_class_label(self) -> str | None:
        label = self.value.strip()
        if not label:
            return None

        return label


class DetectionCountCondition(ConditionModel):
    field: Literal["detection_count"] = "detection_count"
    operator: NumericComparisonOperator = "gte"
    value: int = Field(default=1, ge=0, le=1000)

    def matches(self, event: DetectionEvent) -> bool:
        return compare_number(len(event.detections), self.operator, self.value)


class MaxConfidenceCondition(ConditionModel):
    field: Literal["max_confidence"] = "max_confidence"
    operator: NumericComparisonOperator = "gte"
    value: float = Field(default=0.5, ge=0.0, le=1.0)

    def matches(self, event: DetectionEvent) -> bool:
        confidence = max(
            (detection.confidence for detection in event.detections),
            default=0.0,
        )

        return compare_number(confidence, self.operator, self.value)


IfElseCondition = Annotated[
    EventKindCondition | ObjectClassCondition | DetectionCountCondition | MaxConfidenceCondition,
    Field(discriminator="field"),
]


class RunnableEventKindCondition(EventKindCondition):
    value: EventKind


class RunnableObjectClassCondition(ObjectClassCondition):
    value: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]


RunnableIfElseCondition = Annotated[
    RunnableEventKindCondition
    | RunnableObjectClassCondition
    | DetectionCountCondition
    | MaxConfidenceCondition,
    Field(discriminator="field"),
]
