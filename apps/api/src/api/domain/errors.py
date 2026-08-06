"""Typed workflow-graph failures with one message registry."""

from enum import StrEnum


class GraphErrorCode(StrEnum):
    DUPLICATE_NODE_IDS = "duplicate_node_ids"
    DUPLICATE_EDGE_ID = "duplicate_edge_id"
    EDGE_NODE_MISSING = "edge_node_missing"
    BRANCH_ON_NON_FILTER = "branch_on_non_filter"
    NO_CAMERA_SOURCE = "no_camera_source"
    GRAPH_CYCLE = "graph_cycle"
    NODE_NOT_RUNNABLE = "node_not_runnable"
    FEATURE_NOT_LICENSED = "feature_not_licensed"
    MULTIPLE_DETECT_NODES = "multiple_detect_nodes"
    DETECT_NODE_MISSING = "detect_node_missing"
    MODEL_NOT_SELECTED = "model_not_selected"
    MODEL_UNAVAILABLE = "model_unavailable"
    ASSET_STORE_NOT_CONFIGURED = "asset_store_not_configured"
    ASSET_UNAVAILABLE = "asset_unavailable"
    CREDENTIAL_UNAVAILABLE = "credential_unavailable"
    CREDENTIAL_TYPE_MISMATCH = "credential_type_mismatch"
    UNSUPPORTED_EVENT_KINDS = "unsupported_event_kinds"
    UNSUPPORTED_CLASSES = "unsupported_classes"
    UNSUPPORTED_CONDITION_EVENT = "unsupported_condition_event"
    UNSUPPORTED_CONDITION_CLASS = "unsupported_condition_class"


_MESSAGES: dict[GraphErrorCode, str] = {
    GraphErrorCode.DUPLICATE_NODE_IDS: "duplicate node ids: {names}",
    GraphErrorCode.DUPLICATE_EDGE_ID: "duplicate edge id: {edge_id}",
    GraphErrorCode.EDGE_NODE_MISSING: "edge '{edge_id}' references a missing node",
    GraphErrorCode.BRANCH_ON_NON_FILTER: (
        "edge '{edge_id}' uses branch '{branch}' but its source is not a filter"
    ),
    GraphErrorCode.NO_CAMERA_SOURCE: "workflow requires at least one camera source",
    GraphErrorCode.GRAPH_CYCLE: "workflow contains a cycle through node '{node_id}'",
    GraphErrorCode.NODE_NOT_RUNNABLE: "node '{node_id}' is not runnable: {reason}",
    GraphErrorCode.FEATURE_NOT_LICENSED: ("node '{node_id}' requires licensed feature '{feature}'"),
    GraphErrorCode.MULTIPLE_DETECT_NODES: (
        "camera source '{node_id}' reaches multiple detect nodes: {names}"
    ),
    GraphErrorCode.DETECT_NODE_MISSING: (
        "camera source '{node_id}' must reach exactly one detect node"
    ),
    GraphErrorCode.MODEL_NOT_SELECTED: "detect node '{node_id}' has no model selected",
    GraphErrorCode.MODEL_UNAVAILABLE: (
        "detect node '{node_id}' selects unavailable model '{model_id}'"
    ),
    GraphErrorCode.ASSET_STORE_NOT_CONFIGURED: (
        "camera source '{node_id}' uses a file asset but the asset store is not configured"
    ),
    GraphErrorCode.ASSET_UNAVAILABLE: (
        "camera source '{node_id}' references missing asset '{key}'"
    ),
    GraphErrorCode.CREDENTIAL_UNAVAILABLE: (
        "action node '{node_id}' references a missing credential"
    ),
    GraphErrorCode.CREDENTIAL_TYPE_MISMATCH: (
        "action node '{node_id}' needs a '{expected}' credential but got '{actual}'"
    ),
    GraphErrorCode.UNSUPPORTED_EVENT_KINDS: (
        "detect node '{node_id}' selects events unsupported by model '{model_id}': {names}"
    ),
    GraphErrorCode.UNSUPPORTED_CLASSES: (
        "class filter '{node_id}' selects classes unsupported by its upstream models: {names}"
    ),
    GraphErrorCode.UNSUPPORTED_CONDITION_EVENT: (
        "if/else node '{node_id}' selects event '{value}' unsupported by upstream models '{models}'"
    ),
    GraphErrorCode.UNSUPPORTED_CONDITION_CLASS: (
        "if/else node '{node_id}' selects class '{value}' unsupported by upstream models '{models}'"
    ),
}


class WorkflowGraphError(ValueError):
    """The graph is valid JSON but cannot run; carries a stable code and node context."""

    def __init__(
        self,
        code: GraphErrorCode,
        *,
        node_id: str | None = None,
        **details: str,
    ) -> None:
        self.code = code
        self.node_id = node_id
        super().__init__(_MESSAGES[code].format(node_id=node_id, **details))
