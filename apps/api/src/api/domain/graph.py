"""Validated index over a workflow graph."""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

from api.domain.errors import GraphErrorCode, WorkflowGraphError
from api.domain.workflow import (
    CameraSourceData,
    DetectData,
    FilterNodeData,
    NodeDataUnion,
    WorkflowEdge,
    WorkflowGraph,
)


@dataclass(frozen=True, slots=True)
class SelectedDetect:
    """A source's single Detect node with a model guaranteed to be selected."""

    node_id: str
    model_id: str
    data: DetectData


@dataclass(frozen=True, slots=True)
class WorkflowGraphIndex:
    nodes_by_id: dict[str, NodeDataUnion]
    adjacency: dict[str, tuple[str, ...]]
    reverse_adjacency: dict[str, tuple[str, ...]]
    outgoing_edges: dict[str, tuple[WorkflowEdge, ...]]

    @classmethod
    def build(cls, graph: WorkflowGraph) -> WorkflowGraphIndex:
        nodes_by_id: dict[str, NodeDataUnion] = {}
        duplicates: set[str] = set()

        for node in graph.nodes:
            if node.id in nodes_by_id:
                duplicates.add(node.id)
            nodes_by_id[node.id] = node.data

        if duplicates:
            names = ", ".join(sorted(duplicates))
            raise WorkflowGraphError(GraphErrorCode.DUPLICATE_NODE_IDS, names=names)

        adjacency: dict[str, list[str]] = defaultdict(list)
        reverse_adjacency: dict[str, list[str]] = defaultdict(list)
        outgoing_edges: dict[str, list[WorkflowEdge]] = defaultdict(list)
        edge_ids: set[str] = set()

        for edge in graph.edges:
            if edge.id in edge_ids:
                raise WorkflowGraphError(GraphErrorCode.DUPLICATE_EDGE_ID, edge_id=edge.id)
            edge_ids.add(edge.id)

            if edge.source not in nodes_by_id or edge.target not in nodes_by_id:
                raise WorkflowGraphError(GraphErrorCode.EDGE_NODE_MISSING, edge_id=edge.id)

            if edge.branch is not None and not isinstance(nodes_by_id[edge.source], FilterNodeData):
                raise WorkflowGraphError(
                    GraphErrorCode.BRANCH_ON_NON_FILTER,
                    edge_id=edge.id,
                    branch=edge.branch,
                )

            adjacency[edge.source].append(edge.target)
            reverse_adjacency[edge.target].append(edge.source)
            outgoing_edges[edge.source].append(edge)

        return cls(
            nodes_by_id=nodes_by_id,
            adjacency={node_id: tuple(targets) for node_id, targets in adjacency.items()},
            reverse_adjacency={
                node_id: tuple(sources) for node_id, sources in reverse_adjacency.items()
            },
            outgoing_edges={node_id: tuple(edges) for node_id, edges in outgoing_edges.items()},
        )

    def source_nodes(self) -> dict[str, CameraSourceData]:
        return {
            node_id: data
            for node_id, data in self.nodes_by_id.items()
            if isinstance(data, CameraSourceData)
        }

    def reachable_from(self, start_node_id: str) -> set[str]:
        return self._collect_reachable(start_node_id, self.adjacency)

    def ancestors_of(self, node_id: str) -> set[str]:
        return self._collect_reachable(node_id, self.reverse_adjacency)

    def detect_for_source(self, source_node_id: str) -> tuple[str, DetectData] | None:
        detects = [
            (node_id, data)
            for node_id in self.reachable_from(source_node_id)
            if isinstance((data := self.nodes_by_id[node_id]), DetectData)
        ]
        if len(detects) > 1:
            names = ", ".join(sorted(node_id for node_id, _data in detects))
            raise WorkflowGraphError(
                GraphErrorCode.MULTIPLE_DETECT_NODES,
                node_id=source_node_id,
                names=names,
            )

        return detects[0] if detects else None

    def selected_detect_for_source(self, source_node_id: str) -> SelectedDetect:
        detected = self.detect_for_source(source_node_id)
        if detected is None:
            raise WorkflowGraphError(GraphErrorCode.DETECT_NODE_MISSING, node_id=source_node_id)

        detect_node_id, detect = detected
        if detect.model_id is None:
            raise WorkflowGraphError(GraphErrorCode.MODEL_NOT_SELECTED, node_id=detect_node_id)

        return SelectedDetect(node_id=detect_node_id, model_id=detect.model_id, data=detect)

    @staticmethod
    def _collect_reachable(
        start_node_id: str,
        adjacency: dict[str, tuple[str, ...]],
    ) -> set[str]:
        visited: set[str] = set()
        queue = deque(adjacency.get(start_node_id, ()))

        while queue:
            node_id = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)
            queue.extend(adjacency.get(node_id, ()))

        return visited
