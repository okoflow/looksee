from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, FiniteFloat, model_validator

from shared.contracts.values import ModelId


class Detection(BaseModel):
    """One detected object within a frame."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str = Field(
        min_length=1,
        max_length=128,
        description="Class label resolved from the model bundle manifest.",
    )
    bounding_box: tuple[FiniteFloat, FiniteFloat, FiniteFloat, FiniteFloat] = Field(
        description="Pixel corner coordinates in xyxy order: x_min, y_min, x_max, y_max.",
    )
    confidence: float = Field(ge=0.0, le=1.0)
    class_id: int = Field(ge=0)
    tracker_id: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_bounding_box(self) -> Self:
        x_min, y_min, x_max, y_max = self.bounding_box
        if x_min > x_max or y_min > y_max:
            raise ValueError("bounding_box minimums must not exceed maximums")

        return self


class RunIdentity(BaseModel):
    """Fields naming the exact worker run an artifact came from."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    camera_id: UUID
    workflow_id: UUID
    revision: int = Field(ge=0)
    run_id: UUID
    model_id: ModelId
    timestamp: AwareDatetime


class DetectionFrame(RunIdentity):
    """Inference output for one camera at one moment: the inference -> API contract."""

    frame_width: int = Field(ge=1, description="Decoded frame width in pixels.")
    frame_height: int = Field(ge=1, description="Decoded frame height in pixels.")
    detections: tuple[Detection, ...]


class WorkerStarted(RunIdentity):
    """Worker began processing frames."""

    type: Literal["worker_started"] = "worker_started"


class WorkerErrored(RunIdentity):
    """Worker terminated because of an error."""

    type: Literal["worker_errored"] = "worker_errored"
    reason: str | None = Field(default=None, max_length=500)


class WorkerStopped(RunIdentity):
    """Worker stopped cleanly after a Stop command."""

    type: Literal["worker_stopped"] = "worker_stopped"


WorkerEvent = Annotated[
    WorkerStarted | WorkerErrored | WorkerStopped,
    Field(discriminator="type"),
]
