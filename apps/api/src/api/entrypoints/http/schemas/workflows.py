"""Workflow HTTP request and response bodies."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from api.application.workflows import WorkflowDescription, WorkflowName
from api.domain.enums import CameraSource, CameraStatus
from api.domain.workflow import WorkflowGraph


class WorkflowCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: WorkflowName
    description: WorkflowDescription | None = None
    graph: WorkflowGraph = Field(default_factory=WorkflowGraph)


class WorkflowCameraRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    node_id: str
    name: str
    source_type: CameraSource
    status: CameraStatus


class WorkflowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str | None
    enabled: bool
    graph: WorkflowGraph
    cameras: list[WorkflowCameraRead]
    created_at: datetime
    updated_at: datetime
