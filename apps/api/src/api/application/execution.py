"""Evaluate one detection event through a validated workflow graph."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import replace
from typing import TYPE_CHECKING, Any, assert_never
from uuid import UUID

from pydantic.dataclasses import dataclass

from api.application.errors import RetryableFrameError
from api.domain.workflow import (
    ActionNodeData,
    CameraSourceData,
    DetectData,
    FilterNodeData,
    FilterRuntime,
)

if TYPE_CHECKING:
    from zoneinfo import ZoneInfo

    from api.domain.events import DetectionEvent
    from api.domain.graph import WorkflowGraphIndex
    from api.domain.workflow import RuntimeState, WorkflowEdge

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ExecutionIdentity:
    workflow_id: UUID
    run_id: UUID
    camera_name: str
    node_id: str = ""


type ActionRunner = Callable[
    [ExecutionIdentity, DetectionEvent, ActionNodeData, dict[str, Any]],
    Awaitable[None],
]


class _EventExecutor:
    def __init__(
        self,
        index: WorkflowGraphIndex,
        identity: ExecutionIdentity,
        event: DetectionEvent,
        event_timezone: ZoneInfo,
        runtime_state: RuntimeState,
        run_action: ActionRunner,
    ) -> None:
        self._index = index
        self._identity = identity
        self._event = event
        self._event_timezone = event_timezone
        self._runtime_state = runtime_state
        self._action_runner = run_action
        self._visited: set[str] = set()
        self._context: dict[str, Any] = {}

    async def run(self, source_node_id: str) -> None:
        if source_node_id in self._index.nodes_by_id:
            await self._walk(source_node_id)

    async def _walk(self, node_id: str) -> None:
        if node_id in self._visited:
            return
        self._visited.add(node_id)

        data = self._index.nodes_by_id.get(node_id)
        if data is None:
            return

        if isinstance(data, FilterNodeData):
            await self._walk_filter(node_id, data)
            return
        if isinstance(data, DetectData):
            if not data.passes(self._event):
                return
        elif isinstance(data, ActionNodeData):
            await self._run_action(node_id, data)
        elif not isinstance(data, CameraSourceData):
            assert_never(data)

        await self._walk_edges(self._index.outgoing_edges.get(node_id, ()))

    async def _walk_filter(self, node_id: str, data: FilterNodeData) -> None:
        runtime = FilterRuntime(
            workflow_id=self._identity.workflow_id,
            run_id=self._identity.run_id,
            node_id=node_id,
            timezone=self._event_timezone,
            state=self._runtime_state,
        )
        selected_branch = "if" if data.passes(self._event, runtime) else "else"

        edges = (
            edge
            for edge in self._index.outgoing_edges.get(node_id, ())
            if edge.effective_branch == selected_branch
        )
        await self._walk_edges(edges)

    async def _walk_edges(self, edges: Iterable[WorkflowEdge]) -> None:
        for edge in edges:
            await self._walk(edge.target)

    async def _run_action(self, node_id: str, data: ActionNodeData) -> None:
        try:
            await self._action_runner(
                replace(self._identity, node_id=node_id),
                self._event,
                data,
                self._context,
            )
        except RetryableFrameError:
            raise
        except Exception:
            logger.exception(
                "action failed node=%s workflow=%s",
                node_id,
                self._identity.workflow_id,
            )


async def execute_event(
    index: WorkflowGraphIndex,
    source_node_id: str,
    identity: ExecutionIdentity,
    event: DetectionEvent,
    event_timezone: ZoneInfo,
    runtime_state: RuntimeState,
    run_action: ActionRunner,
) -> None:
    executor = _EventExecutor(
        index,
        identity,
        event,
        event_timezone,
        runtime_state=runtime_state,
        run_action=run_action,
    )
    await executor.run(source_node_id)
