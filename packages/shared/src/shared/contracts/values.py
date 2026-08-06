from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

ModelId = Annotated[str, Field(pattern=r"^[a-z0-9_-]+$", min_length=1, max_length=64)]


class WorkflowConfig(BaseModel):
    """Runtime parameters that shape one workflow's inference behavior."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: ModelId = Field(description="Immutable id of the selected model asset.")
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    inference_fps: int = Field(default=1, ge=1, le=15)
