"""Graph-level runnability checks against reachable nodes and the model catalog.

Field-level node rules live in the runnable node models; this module only knows
graph shape (sources, cycles, detect resolution) and cross-node vocabulary
compatibility with the models a source can reach.
"""

from dataclasses import dataclass
from typing import Protocol

from api.application.entitlements import Entitlements
from api.domain.errors import GraphErrorCode, WorkflowGraphError
from api.domain.graph import WorkflowGraphIndex
from api.domain.models import ModelDescriptor
from api.domain.workflow import (
    LICENSED_FEATURES_BY_KIND,
    ClassFilterData,
    DetectData,
    IfElseFilterData,
    ensure_node_runnable,
)


class ModelCatalogReader(Protocol):
    def get(self, model_id: str) -> ModelDescriptor | None: ...


@dataclass(frozen=True, slots=True)
class _SourceCapabilities:
    model_id: str
    labels: frozenset[str]
    event_kinds: frozenset[str]


def validate_runnable_graph(
    index: WorkflowGraphIndex,
    catalog: ModelCatalogReader,
    entitlements: Entitlements,
) -> None:
    sources = index.source_nodes()
    if not sources:
        raise WorkflowGraphError(GraphErrorCode.NO_CAMERA_SOURCE)

    _validate_acyclic(index, set(sources))
    _validate_features_licensed(index, entitlements)

    for node_id in sorted(index.nodes_by_id):
        ensure_node_runnable(node_id, index.nodes_by_id[node_id])

    _validate_models_available(index, catalog)

    source_capabilities = {
        source_node_id: _resolve_source_capabilities(index, source_node_id, catalog)
        for source_node_id in sources
    }
    _validate_vocabulary_filters(index, source_capabilities)


def _validate_features_licensed(index: WorkflowGraphIndex, entitlements: Entitlements) -> None:
    """Every commercial node type in the graph must be covered by the license."""
    for node_id in sorted(index.nodes_by_id):
        feature = LICENSED_FEATURES_BY_KIND.get(index.nodes_by_id[node_id].kind)
        if feature is None:
            continue

        if entitlements.allows(feature):
            continue

        raise WorkflowGraphError(
            GraphErrorCode.FEATURE_NOT_LICENSED,
            node_id=node_id,
            feature=feature,
        )


def _validate_models_available(index: WorkflowGraphIndex, catalog: ModelCatalogReader) -> None:
    """Every detect node must reference an installed model, reachable or not."""
    for node_id in sorted(index.nodes_by_id):
        data = index.nodes_by_id[node_id]
        if not isinstance(data, DetectData):
            continue

        if data.model_id is None:
            continue

        if catalog.get(data.model_id) is None:
            raise WorkflowGraphError(
                GraphErrorCode.MODEL_UNAVAILABLE,
                node_id=node_id,
                model_id=data.model_id,
            )


def _validate_acyclic(index: WorkflowGraphIndex, source_node_ids: set[str]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> None:
        if node_id in visiting:
            raise WorkflowGraphError(GraphErrorCode.GRAPH_CYCLE, node_id=node_id)

        if node_id in visited:
            return

        visiting.add(node_id)
        for target_id in index.adjacency.get(node_id, ()):
            visit(target_id)
        visiting.remove(node_id)
        visited.add(node_id)

    for source_node_id in source_node_ids:
        visit(source_node_id)


def _resolve_source_capabilities(
    index: WorkflowGraphIndex,
    source_node_id: str,
    catalog: ModelCatalogReader,
) -> _SourceCapabilities:
    selected = index.selected_detect_for_source(source_node_id)

    model = catalog.get(selected.model_id)
    if model is None:
        raise WorkflowGraphError(
            GraphErrorCode.MODEL_UNAVAILABLE,
            node_id=selected.node_id,
            model_id=selected.model_id,
        )

    _validate_detect_events(selected.node_id, selected.data, model)

    return _source_capabilities(selected.data, model)


def _validate_detect_events(
    detect_node_id: str,
    detect: DetectData,
    model: ModelDescriptor,
) -> None:
    supported_events = {model_class.event_kind for model_class in model.event_classes()}
    unsupported_events = set(detect.event_kinds).difference(supported_events)
    if not unsupported_events:
        return

    raise WorkflowGraphError(
        GraphErrorCode.UNSUPPORTED_EVENT_KINDS,
        node_id=detect_node_id,
        model_id=detect.model_id or "",
        names=", ".join(sorted(unsupported_events)),
    )


def _source_capabilities(detect: DetectData, model: ModelDescriptor) -> _SourceCapabilities:
    selected_events = set(detect.event_kinds)
    reachable_classes = tuple(
        model_class
        for model_class in model.event_classes()
        if not selected_events or model_class.event_kind in selected_events
    )

    return _SourceCapabilities(
        model_id=model.id,
        labels=frozenset(model_class.label for model_class in reachable_classes),
        event_kinds=frozenset(
            model_class.event_kind
            for model_class in reachable_classes
            if model_class.event_kind is not None
        ),
    )


def _validate_vocabulary_filters(
    index: WorkflowGraphIndex,
    source_capabilities: dict[str, _SourceCapabilities],
) -> None:
    source_ids = set(source_capabilities)

    for node_id, data in index.nodes_by_id.items():
        if not isinstance(data, ClassFilterData | IfElseFilterData):
            continue

        upstream = [
            source_capabilities[source_id]
            for source_id in source_ids.intersection(index.ancestors_of(node_id))
        ]
        if not upstream:
            continue

        labels = {label for capabilities in upstream for label in capabilities.labels}
        if isinstance(data, ClassFilterData):
            _validate_class_filter(node_id, data, labels)
        else:
            _validate_if_else_filter(node_id, data, upstream, labels)


def _validate_class_filter(node_id: str, data: ClassFilterData, labels: set[str]) -> None:
    unsupported_labels = set(data.classes).difference(labels)
    if not unsupported_labels:
        return

    raise WorkflowGraphError(
        GraphErrorCode.UNSUPPORTED_CLASSES,
        node_id=node_id,
        names=", ".join(sorted(unsupported_labels)),
    )


def _validate_if_else_filter(
    node_id: str,
    data: IfElseFilterData,
    upstream: list[_SourceCapabilities],
    labels: set[str],
) -> None:
    models = ", ".join(sorted({capabilities.model_id for capabilities in upstream}))
    event_kinds = {
        event_kind for capabilities in upstream for event_kind in capabilities.event_kinds
    }

    event_kind = data.condition.selected_event_kind()
    if event_kind is not None and event_kind not in event_kinds:
        raise WorkflowGraphError(
            GraphErrorCode.UNSUPPORTED_CONDITION_EVENT,
            node_id=node_id,
            value=event_kind,
            models=models,
        )

    class_label = data.condition.selected_class_label()
    if class_label is not None and class_label not in labels:
        raise WorkflowGraphError(
            GraphErrorCode.UNSUPPORTED_CONDITION_CLASS,
            node_id=node_id,
            value=class_label,
            models=models,
        )
