"""Events derived from perception frames and evaluated by workflow policy."""

from typing import Any
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from shared import Detection, EventKind, ModelId

EVENT_KIND_DETECTED_SUFFIX = "_DETECTED"


class DetectionEvent(BaseModel):
    """A model event routed through one persisted workflow graph."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    camera_id: UUID
    workflow_id: UUID
    model_id: ModelId
    kind: EventKind
    ts: AwareDatetime
    frame_width: int = Field(ge=1)
    frame_height: int = Field(ge=1)
    detections: list[Detection] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
