"""Graph-level runnability checks: shape, licensing, model vocabulary."""

import pytest

from api.application.entitlements import COMMUNITY_ENTITLEMENTS, Entitlements
from api.application.workflow_validation import validate_runnable_graph
from api.domain.errors import GraphErrorCode, WorkflowGraphError
from api.domain.graph import WorkflowGraphIndex

ENTERPRISE = Entitlements(
    edition="enterprise",
    features=frozenset({"measurement_filters", "enterprise_integrations"}),
)
LINEAR = [("cam", "det"), ("det", "alert")]


@pytest.fixture
def validate(catalog, build_graph):
    def _validate(nodes, edges, entitlements=COMMUNITY_ENTITLEMENTS):
        index = WorkflowGraphIndex.build(build_graph(nodes, edges))
        validate_runnable_graph(index, catalog, entitlements)

    return _validate


@pytest.fixture
def expect_error(validate):
    def _expect(nodes, edges, code, node_id=None, entitlements=COMMUNITY_ENTITLEMENTS):
        with pytest.raises(WorkflowGraphError) as excinfo:
            validate(nodes, edges, entitlements)

        assert excinfo.value.code is code
        assert excinfo.value.node_id == node_id

        return str(excinfo.value)

    return _expect


def test_minimal_linear_graph_is_runnable(validate, basic_nodes):
    validate(basic_nodes, LINEAR)


def test_graph_without_camera_source_is_rejected(expect_error, basic_nodes):
    del basic_nodes["cam"]

    expect_error(basic_nodes, [("det", "alert")], GraphErrorCode.NO_CAMERA_SOURCE)


def test_cycle_is_reported_on_the_node_that_closes_it(expect_error, basic_nodes):
    basic_nodes["gate"] = {"kind": "if_else_filter", "condition": {"field": "detection_count"}}
    edges = [("cam", "det"), ("det", "gate"), ("gate", "det"), ("gate", "alert", "else")]

    expect_error(basic_nodes, edges, GraphErrorCode.GRAPH_CYCLE, node_id="det")


def test_cycle_check_precedes_license_check(expect_error, basic_nodes):
    basic_nodes["line"] = {"kind": "line_crossing_filter"}
    edges = [("cam", "det"), ("det", "line"), ("line", "det")]

    expect_error(basic_nodes, edges, GraphErrorCode.GRAPH_CYCLE, node_id="det")


def test_detect_without_model_is_not_runnable(expect_error, basic_nodes):
    basic_nodes["det"] = {"kind": "detect"}

    message = expect_error(basic_nodes, LINEAR, GraphErrorCode.NODE_NOT_RUNNABLE, node_id="det")

    assert "model_id" in message


def test_detect_selecting_unknown_model_is_rejected(expect_error, basic_nodes):
    basic_nodes["det"]["model_id"] = "ghost"

    message = expect_error(basic_nodes, LINEAR, GraphErrorCode.MODEL_UNAVAILABLE, node_id="det")

    assert "'ghost'" in message


def test_disconnected_detect_still_needs_an_installed_model(expect_error, basic_nodes):
    basic_nodes["orphan"] = {"kind": "detect", "model_id": "ghost"}

    expect_error(basic_nodes, LINEAR, GraphErrorCode.MODEL_UNAVAILABLE, node_id="orphan")


def test_detect_selecting_events_the_model_lacks_is_rejected(expect_error, basic_nodes):
    basic_nodes["det"]["event_kinds"] = ["PERSON_DETECTED", "DOG_DETECTED"]

    message = expect_error(
        basic_nodes, LINEAR, GraphErrorCode.UNSUPPORTED_EVENT_KINDS, node_id="det"
    )

    assert message.endswith(": DOG_DETECTED")


def test_source_must_reach_a_detect_node(expect_error, basic_nodes):
    expect_error(basic_nodes, [("det", "alert")], GraphErrorCode.DETECT_NODE_MISSING, node_id="cam")


def test_source_reaching_two_detect_nodes_is_rejected(expect_error, basic_nodes):
    basic_nodes["det2"] = {"kind": "detect", "model_id": "people"}
    edges = [("cam", "det"), ("cam", "det2"), ("det", "alert")]

    message = expect_error(basic_nodes, edges, GraphErrorCode.MULTIPLE_DETECT_NODES, node_id="cam")

    assert message.endswith(": det, det2")


def test_class_filter_may_only_select_upstream_labels(expect_error, basic_nodes):
    basic_nodes["cls"] = {"kind": "class_filter", "classes": ["person", "dog"]}
    edges = [("cam", "det"), ("det", "cls"), ("cls", "alert")]

    message = expect_error(basic_nodes, edges, GraphErrorCode.UNSUPPORTED_CLASSES, node_id="cls")

    assert message.endswith(": dog")


def test_class_filter_with_upstream_labels_passes(validate, basic_nodes):
    basic_nodes["cls"] = {"kind": "class_filter", "classes": ["person", "car"]}

    validate(basic_nodes, [("cam", "det"), ("det", "cls"), ("cls", "alert")])


def test_class_filter_without_upstream_source_is_not_vocabulary_checked(validate, basic_nodes):
    basic_nodes["cls"] = {"kind": "class_filter", "classes": ["dog"]}

    validate(basic_nodes, LINEAR)


def test_detect_event_selection_narrows_downstream_labels(expect_error, basic_nodes):
    basic_nodes["det"]["event_kinds"] = ["CAR_DETECTED"]
    basic_nodes["cls"] = {"kind": "class_filter", "classes": ["person"]}
    edges = [("cam", "det"), ("det", "cls"), ("cls", "alert")]

    expect_error(basic_nodes, edges, GraphErrorCode.UNSUPPORTED_CLASSES, node_id="cls")


def test_if_else_event_condition_must_match_upstream_events(expect_error, basic_nodes):
    basic_nodes["gate"] = {
        "kind": "if_else_filter",
        "condition": {"field": "event_kind", "value": "DOG_DETECTED"},
    }
    edges = [("cam", "det"), ("det", "gate"), ("gate", "alert", "if")]

    message = expect_error(
        basic_nodes, edges, GraphErrorCode.UNSUPPORTED_CONDITION_EVENT, node_id="gate"
    )

    assert "'DOG_DETECTED'" in message
    assert "'people'" in message


def test_if_else_class_condition_must_match_upstream_labels(expect_error, basic_nodes):
    basic_nodes["gate"] = {
        "kind": "if_else_filter",
        "condition": {"field": "object_class", "value": "dog"},
    }
    edges = [("cam", "det"), ("det", "gate"), ("gate", "alert", "else")]

    expect_error(basic_nodes, edges, GraphErrorCode.UNSUPPORTED_CONDITION_CLASS, node_id="gate")


@pytest.mark.parametrize(
    "condition",
    [
        {"field": "event_kind", "value": "PERSON_DETECTED"},
        {"field": "object_class", "value": "car"},
        {"field": "detection_count", "operator": "gt", "value": 3},
        {"field": "max_confidence", "operator": "lt", "value": 0.2},
    ],
)
def test_if_else_with_compatible_condition_passes(validate, basic_nodes, condition):
    basic_nodes["gate"] = {"kind": "if_else_filter", "condition": condition}
    edges = [("cam", "det"), ("det", "gate"), ("gate", "alert", "if"), ("gate", "alert", "else")]

    validate(basic_nodes, edges)


@pytest.mark.parametrize(
    ("node", "feature"),
    [
        ({"kind": "line_crossing_filter", "line": [[0.1, 0.5], [0.9, 0.5]]}, "measurement_filters"),
        (
            {"kind": "dwell_filter", "polygon": [[0, 0], [1, 0], [1, 1]], "min_seconds": 5},
            "measurement_filters",
        ),
        ({"kind": "count_threshold_filter", "count": 2}, "measurement_filters"),
        (
            {
                "kind": "slack_action",
                "credential_id": "5f1c6d4a-2d7e-4c1a-9b1e-3c2f1a0b9d8e",
            },
            "enterprise_integrations",
        ),
    ],
)
def test_enterprise_nodes_need_their_feature_licensed(
    expect_error, validate, basic_nodes, node, feature
):
    basic_nodes["ent"] = node
    edges = [("cam", "det"), ("det", "ent")]

    message = expect_error(basic_nodes, edges, GraphErrorCode.FEATURE_NOT_LICENSED, node_id="ent")
    validate(basic_nodes, edges, ENTERPRISE)

    assert f"'{feature}'" in message


@pytest.mark.parametrize(
    ("node", "reason_field"),
    [
        ({"kind": "camera_source", "source_type": "rtsp", "url": ""}, "url"),
        ({"kind": "camera_source", "source_type": "rtsp", "url": "http://cam/stream"}, "url"),
        ({"kind": "camera_source", "source_type": "rtmp", "url": "rtsp://cam/stream"}, "url"),
        ({"kind": "camera_source", "source_type": "srt", "url": "rtsp://cam/live"}, "url"),
        ({"kind": "camera_source", "source_type": "whep", "url": "rtsp://cam/whep"}, "url"),
        ({"kind": "camera_source", "source_type": "file", "url": "../escape.mp4"}, "url"),
        ({"kind": "camera_source", "source_type": "file", "url": ".hidden.mp4"}, "url"),
    ],
)
def test_source_urls_must_match_their_ingest_type(expect_error, basic_nodes, node, reason_field):
    basic_nodes["cam"] = node

    message = expect_error(basic_nodes, LINEAR, GraphErrorCode.NODE_NOT_RUNNABLE, node_id="cam")

    assert f"{reason_field}:" in message


@pytest.mark.parametrize(
    "node",
    [
        {"kind": "camera_source", "source_type": "rtsp", "url": "rtsps://cam:8322/live"},
        {"kind": "camera_source", "source_type": "rtmp", "url": "rtmp://cam/live"},
        {"kind": "camera_source", "source_type": "srt", "url": "srt://cam:9000"},
        {"kind": "camera_source", "source_type": "whep", "url": "https://cam/whep"},
        {"kind": "camera_source", "source_type": "webrtc", "url": ""},
        {"kind": "camera_source", "source_type": "file", "url": "clips/lobby_01.mp4"},
    ],
)
def test_well_formed_sources_are_runnable(validate, basic_nodes, node):
    basic_nodes["cam"] = node

    validate(basic_nodes, LINEAR)


@pytest.mark.parametrize(
    ("node", "reason_field"),
    [
        ({"kind": "zone_filter", "polygon": [[0, 0], [1, 1]]}, "polygon"),
        ({"kind": "if_else_filter", "condition": {"field": "event_kind"}}, "condition"),
        (
            {"kind": "if_else_filter", "condition": {"field": "object_class", "value": " "}},
            "condition",
        ),
        ({"kind": "time_window_filter", "weekdays": []}, "weekdays"),
        ({"kind": "telegram_action", "chat_id": "42"}, "credential_id"),
        (
            {"kind": "telegram_action", "credential_id": "5f1c6d4a-2d7e-4c1a-9b1e-3c2f1a0b9d8e"},
            "chat_id",
        ),
        ({"kind": "webhook_action", "url": "not a url"}, "url"),
        ({"kind": "email_action", "credential_id": "5f1c6d4a-2d7e-4c1a-9b1e-3c2f1a0b9d8e"}, "to"),
        (
            {
                "kind": "mqtt_action",
                "credential_id": "5f1c6d4a-2d7e-4c1a-9b1e-3c2f1a0b9d8e",
                "topic": "  ",
            },
            "topic",
        ),
        ({"kind": "discord_action", "credential_id": "nope"}, "credential_id"),
    ],
)
def test_nodes_missing_runtime_preconditions_are_not_runnable(
    expect_error, basic_nodes, node, reason_field
):
    basic_nodes["node"] = node
    edges = [("cam", "det"), ("det", "node")]

    message = expect_error(basic_nodes, edges, GraphErrorCode.NODE_NOT_RUNNABLE, node_id="node")

    assert f"{reason_field}" in message


def test_node_ids_are_checked_in_sorted_order(expect_error, basic_nodes):
    basic_nodes["b_zone"] = {"kind": "zone_filter"}
    basic_nodes["a_zone"] = {"kind": "zone_filter"}

    expect_error(basic_nodes, LINEAR, GraphErrorCode.NODE_NOT_RUNNABLE, node_id="a_zone")


def test_edge_branch_is_only_allowed_out_of_filters(build_graph, basic_nodes):
    graph = build_graph(basic_nodes, [("cam", "det"), ("det", "alert", "else")])

    with pytest.raises(WorkflowGraphError) as excinfo:
        WorkflowGraphIndex.build(graph)

    assert excinfo.value.code is GraphErrorCode.BRANCH_ON_NON_FILTER
    assert "'det->alert:else'" in str(excinfo.value)


def test_edge_to_unknown_node_is_rejected(build_graph, basic_nodes):
    graph = build_graph(basic_nodes, [("cam", "det"), ("det", "ghost")])

    with pytest.raises(WorkflowGraphError) as excinfo:
        WorkflowGraphIndex.build(graph)

    assert excinfo.value.code is GraphErrorCode.EDGE_NODE_MISSING


def test_duplicate_edge_ids_are_rejected(build_graph, basic_nodes):
    graph = build_graph(basic_nodes, [("cam", "det"), ("cam", "det")])

    with pytest.raises(WorkflowGraphError) as excinfo:
        WorkflowGraphIndex.build(graph)

    assert excinfo.value.code is GraphErrorCode.DUPLICATE_EDGE_ID
