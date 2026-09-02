"""Graph error codes and message formatting."""

import pytest

from api.domain.errors import GraphErrorCode, WorkflowGraphError

DETAILS = {
    GraphErrorCode.DUPLICATE_NODE_IDS: {"names": "a, b"},
    GraphErrorCode.DUPLICATE_EDGE_ID: {"edge_id": "e1"},
    GraphErrorCode.EDGE_NODE_MISSING: {"edge_id": "e1"},
    GraphErrorCode.BRANCH_ON_NON_FILTER: {"edge_id": "e1", "branch": "else"},
    GraphErrorCode.NO_CAMERA_SOURCE: {},
    GraphErrorCode.GRAPH_CYCLE: {},
    GraphErrorCode.NODE_NOT_RUNNABLE: {"reason": "url: empty"},
    GraphErrorCode.FEATURE_NOT_LICENSED: {"feature": "measurement_filters"},
    GraphErrorCode.MULTIPLE_DETECT_NODES: {"names": "d1, d2"},
    GraphErrorCode.DETECT_NODE_MISSING: {},
    GraphErrorCode.MODEL_NOT_SELECTED: {},
    GraphErrorCode.MODEL_UNAVAILABLE: {"model_id": "yolo"},
    GraphErrorCode.ASSET_STORE_NOT_CONFIGURED: {},
    GraphErrorCode.ASSET_UNAVAILABLE: {"key": "clips/demo.mp4"},
    GraphErrorCode.CREDENTIAL_UNAVAILABLE: {},
    GraphErrorCode.CREDENTIAL_TYPE_MISMATCH: {"expected": "smtp", "actual": "mqtt"},
    GraphErrorCode.UNSUPPORTED_EVENT_KINDS: {"model_id": "yolo", "names": "CAT_DETECTED"},
    GraphErrorCode.UNSUPPORTED_CLASSES: {"names": "cat"},
    GraphErrorCode.UNSUPPORTED_CONDITION_EVENT: {"value": "CAT_DETECTED", "models": "yolo"},
    GraphErrorCode.UNSUPPORTED_CONDITION_CLASS: {"value": "cat", "models": "yolo"},
}


def test_every_code_is_covered_by_this_module():
    assert set(DETAILS) == set(GraphErrorCode)


def test_codes_are_their_lowercase_names():
    for code in GraphErrorCode:
        assert code.value == code.name.lower()


@pytest.mark.parametrize(("code", "details"), DETAILS.items(), ids=[code.value for code in DETAILS])
def test_message_embeds_every_detail(code, details):
    error = WorkflowGraphError(code, node_id="node-1", **details)

    message = str(error)

    for value in details.values():
        assert value in message


def test_carries_code_node_and_formatted_message():
    error = WorkflowGraphError(GraphErrorCode.MODEL_NOT_SELECTED, node_id="detect-1")

    assert error.code is GraphErrorCode.MODEL_NOT_SELECTED
    assert error.node_id == "detect-1"
    assert str(error) == "detect node 'detect-1' has no model selected"


def test_node_id_defaults_to_none():
    error = WorkflowGraphError(GraphErrorCode.NO_CAMERA_SOURCE)

    assert error.node_id is None
    assert str(error) == "workflow requires at least one camera source"


def test_is_a_value_error():
    error = WorkflowGraphError(GraphErrorCode.NO_CAMERA_SOURCE)

    assert isinstance(error, ValueError)


def test_missing_detail_is_a_programming_error():
    with pytest.raises(KeyError, match="edge_id"):
        WorkflowGraphError(GraphErrorCode.DUPLICATE_EDGE_ID)


def test_unknown_code_is_rejected():
    with pytest.raises(KeyError):
        WorkflowGraphError("not_a_code")
