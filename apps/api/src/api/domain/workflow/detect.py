"""Detect node payload: model selection and inference parameters."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import Field

from api.domain.workflow.base import WorkflowModel
from shared import EventKind, ModelId

if TYPE_CHECKING:
    from api.domain.events import DetectionEvent


class DetectData(WorkflowModel):
    kind: Literal["detect"] = "detect"
    model_id: ModelId | None = None
    event_kinds: list[EventKind] = Field(default_factory=list, max_length=64)
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    inference_fps: int = Field(default=1, ge=1, le=15)

    def passes(self, event: DetectionEvent) -> bool:
        return not self.event_kinds or event.kind in self.event_kinds


class RunnableDetectData(DetectData):
    model_id: ModelId
