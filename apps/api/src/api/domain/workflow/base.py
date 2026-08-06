"""Shared base model and value vocabulary for workflow node payloads."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

NormalizedCoordinate = Annotated[float, Field(ge=0.0, le=1.0)]
NormalizedPoint = tuple[NormalizedCoordinate, NormalizedCoordinate]
Weekday = Annotated[int, Field(ge=0, le=6)]
ClassLabel = Annotated[str, Field(min_length=1, max_length=128)]


class WorkflowModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
