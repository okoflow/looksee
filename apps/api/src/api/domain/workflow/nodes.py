"""Workflow graph document: nodes, edges, and the persisted graph."""

from functools import reduce
from operator import or_
from typing import Annotated, Literal

from pydantic import Field

from api.domain.workflow.actions import ActionData
from api.domain.workflow.base import WorkflowModel
from api.domain.workflow.detect import DetectData
from api.domain.workflow.extensions import NODE_EXTENSIONS
from api.domain.workflow.filters import FilterData
from api.domain.workflow.sources import CameraSourceData

NodeDataUnion = reduce(
    or_,
    (extension.draft for extension in NODE_EXTENSIONS),
    CameraSourceData | DetectData | FilterData | ActionData,
)
NodeData = Annotated[NodeDataUnion, Field(discriminator="kind")]


class NodePosition(WorkflowModel):
    x: float
    y: float


class CanvasComment(WorkflowModel):
    id: str = Field(min_length=1, max_length=128)
    position: NodePosition
    text: str = Field(default="", max_length=2000)


class WorkflowNode(WorkflowModel):
    id: str = Field(min_length=1, max_length=128)
    position: NodePosition
    data: NodeData


EdgeBranch = Literal["if", "else"]


class WorkflowEdge(WorkflowModel):
    id: str = Field(min_length=1, max_length=256)
    source: str = Field(min_length=1, max_length=128)
    target: str = Field(min_length=1, max_length=128)
    branch: EdgeBranch | None = None

    @property
    def effective_branch(self) -> EdgeBranch:
        """An unlabeled edge out of a filter follows the positive branch."""
        if self.branch is None:
            return "if"

        return self.branch


class WorkflowGraph(WorkflowModel):
    nodes: list[WorkflowNode] = Field(default_factory=list, max_length=200)
    edges: list[WorkflowEdge] = Field(default_factory=list, max_length=400)
    comments: list[CanvasComment] = Field(default_factory=list, max_length=100)
