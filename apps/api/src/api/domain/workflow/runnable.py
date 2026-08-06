"""Declarative runnable refinement of draft node payloads.

A node type is runnable-checked by one strict counterpart model; the union
below plus the registered commercial extensions is the single registry.
Adding a node type means adding its draft model and, when it has run-time
preconditions, one Runnable* subclass here — nothing else.
"""

from functools import reduce
from operator import or_
from typing import Annotated

from pydantic import Field, TypeAdapter, ValidationError

from api.domain.errors import GraphErrorCode, WorkflowGraphError
from api.domain.workflow.actions import (
    LogAlertActionData,
    RunnableDiscordAction,
    RunnableEmailAction,
    RunnableMqttAction,
    RunnableTelegramAction,
    RunnableWebhookAction,
    SnapshotActionData,
)
from api.domain.workflow.detect import RunnableDetectData
from api.domain.workflow.extensions import NODE_EXTENSIONS
from api.domain.workflow.filters import (
    ClassFilterData,
    DebounceFilterData,
    RunnableIfElseFilter,
    RunnableTimeWindowFilter,
    RunnableZoneFilter,
    SizeFilterData,
)
from api.domain.workflow.nodes import NodeDataUnion
from api.domain.workflow.sources import RunnableCameraSourceData

RunnableNodeDataUnion = reduce(
    or_,
    (extension.runnable for extension in NODE_EXTENSIONS),
    RunnableCameraSourceData
    | RunnableDetectData
    | RunnableIfElseFilter
    | RunnableZoneFilter
    | ClassFilterData
    | DebounceFilterData
    | RunnableTimeWindowFilter
    | SizeFilterData
    | RunnableTelegramAction
    | RunnableWebhookAction
    | LogAlertActionData
    | SnapshotActionData
    | RunnableEmailAction
    | RunnableMqttAction
    | RunnableDiscordAction,
)
RunnableNodeData = Annotated[RunnableNodeDataUnion, Field(discriminator="kind")]

_runnable_node_adapter: TypeAdapter[RunnableNodeData] = TypeAdapter(RunnableNodeData)


def ensure_node_runnable(node_id: str, data: NodeDataUnion) -> None:
    """Check one node's own configuration against its runnable refinement."""
    try:
        _runnable_node_adapter.validate_python(data.model_dump())
    except ValidationError as exc:
        raise WorkflowGraphError(
            GraphErrorCode.NODE_NOT_RUNNABLE,
            node_id=node_id,
            reason=_first_failure(exc),
        ) from exc


def _first_failure(exc: ValidationError) -> str:
    error = exc.errors()[0]
    location = ".".join(str(part) for part in error["loc"])

    return f"{location}: {error['msg']}" if location else error["msg"]
