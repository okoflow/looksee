from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.contracts.values import WorkflowConfig


class StartStream(BaseModel):
    """Start an inference worker for one camera."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["start_stream"] = "start_stream"
    camera_id: UUID
    workflow_id: UUID
    revision: int = Field(ge=0, description="Monotonic desired-state revision for this camera.")
    run_id: UUID = Field(description="Unique desired-run identity.")
    config: WorkflowConfig


class StopStream(BaseModel):
    """Stop an inference worker for one camera."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    type: Literal["stop_stream"] = "stop_stream"
    camera_id: UUID
    revision: int = Field(ge=0, description="Monotonic desired-state revision for this camera.")
    run_id: UUID | None = Field(
        default=None,
        description="Cancel only this run; None cancels the active run for the camera.",
    )


StreamCommand = Annotated[
    StartStream | StopStream,
    Field(discriminator="type"),
]
