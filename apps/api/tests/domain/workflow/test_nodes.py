"""Workflow graph document: nodes, edges, comments, discriminated node data."""

import math
import typing

import pytest
from pydantic import ValidationError

from api.domain.workflow.detect import DetectData
from api.domain.workflow.extensions import NODE_EXTENSIONS
from api.domain.workflow.filters import ZoneFilterData
from api.domain.workflow.nodes import (
    CanvasComment,
    NodeDataUnion,
    NodePosition,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
)

BUILTIN_KINDS = {
    "camera_source",
    "detect",
    "if_else_filter",
    "zone_filter",
    "class_filter",
    "debounce_filter",
    "time_window_filter",
    "size_filter",
    "telegram_action",
    "webhook_action",
    "log_alert_action",
    "snapshot_action",
    "email_action",
    "mqtt_action",
    "discord_action",
}
NODE_TYPES = typing.get_args(NodeDataUnion)


def kind_of(node_type):
    return node_type.model_fields["kind"].default


def node_values(data):
    return {"id": "n1", "position": {"x": 0, "y": 0}, "data": data}


def test_union_covers_builtin_and_extension_kinds():
    kinds = {kind_of(node_type) for node_type in NODE_TYPES}
    extension_kinds = {extension.kind for extension in NODE_EXTENSIONS}

    assert kinds == BUILTIN_KINDS | extension_kinds


def test_union_kinds_are_unique():
    kinds = [kind_of(node_type) for node_type in NODE_TYPES]

    assert len(kinds) == len(set(kinds))


@pytest.mark.parametrize("node_type", NODE_TYPES, ids=kind_of)
def test_kind_dispatches_to_its_node_class(node_type):
    values = node_values({"kind": kind_of(node_type)})

    node = WorkflowNode.model_validate(values)

    assert type(node.data) is node_type


@pytest.mark.parametrize(
    "data",
    [{"kind": "teleport"}, {}, {"kind": None}, {"kind": "Detect"}],
    ids=["unknown_kind", "missing_kind", "null_kind", "wrong_case"],
)
def test_unknown_or_missing_kind_is_rejected(data):
    with pytest.raises(ValidationError):
        WorkflowNode.model_validate(node_values(data))


def test_dispatched_class_validates_its_own_fields():
    values = node_values({"kind": "zone_filter", "polygon": [(2.0, 0.0)]})

    with pytest.raises(ValidationError, match="polygon"):
        WorkflowNode.model_validate(values)


def test_fields_of_another_kind_are_rejected():
    values = node_values({"kind": "detect", "polygon": []})

    with pytest.raises(ValidationError, match="Extra inputs"):
        WorkflowNode.model_validate(values)


def test_accepts_node_data_instances():
    node = WorkflowNode(
        id="n1", position=NodePosition(x=1.0, y=2.0), data=DetectData(model_id="yolo")
    )

    assert node.data.model_id == "yolo"
    assert node.position == NodePosition(x=1.0, y=2.0)


@pytest.mark.parametrize("node_id", ["", "x" * 129])
def test_node_id_length_is_bounded(node_id):
    values = {**node_values({"kind": "detect"}), "id": node_id}

    with pytest.raises(ValidationError):
        WorkflowNode.model_validate(values)


@pytest.mark.parametrize("field", ["id", "position", "data"])
def test_node_requires_every_field(field):
    values = node_values({"kind": "detect"})
    del values[field]

    with pytest.raises(ValidationError, match=field):
        WorkflowNode.model_validate(values)


def test_node_rejects_unknown_fields():
    values = {**node_values({"kind": "detect"}), "selected": True}

    with pytest.raises(ValidationError):
        WorkflowNode.model_validate(values)


@pytest.mark.parametrize("coordinate", [math.inf, -math.inf, math.nan])
def test_position_rejects_non_finite_coordinates(coordinate):
    with pytest.raises(ValidationError):
        NodePosition(x=coordinate, y=0.0)


def test_position_requires_both_coordinates():
    with pytest.raises(ValidationError, match="y"):
        NodePosition(x=1.0)


def test_position_accepts_negative_coordinates():
    position = NodePosition(x=-120.5, y=-3.0)

    assert (position.x, position.y) == (-120.5, -3.0)


def test_comment_defaults_to_empty_text():
    comment = CanvasComment(id="c1", position=NodePosition(x=0.0, y=0.0))

    assert comment.text == ""


@pytest.mark.parametrize(
    "fields",
    [{"id": ""}, {"id": "x" * 129}, {"text": "x" * 2001}, {"author": "me"}],
    ids=["empty_id", "long_id", "long_text", "unknown_field"],
)
def test_comment_rejects_invalid_fields(fields):
    values = {"id": "c1", "position": {"x": 0, "y": 0}, **fields}

    with pytest.raises(ValidationError):
        CanvasComment.model_validate(values)


def test_edge_defaults_to_no_branch():
    edge = WorkflowEdge(id="e", source="a", target="b")

    assert edge.branch is None


def test_unlabeled_edge_follows_the_positive_branch():
    edge = WorkflowEdge(id="e", source="a", target="b")

    assert edge.effective_branch == "if"


@pytest.mark.parametrize("branch", ["if", "else"])
def test_effective_branch_returns_the_explicit_label(branch):
    edge = WorkflowEdge(id="e", source="a", target="b", branch=branch)

    assert edge.effective_branch == branch


@pytest.mark.parametrize(
    "fields",
    [
        {"branch": "maybe"},
        {"branch": "IF"},
        {"id": ""},
        {"id": "x" * 257},
        {"source": ""},
        {"source": "x" * 129},
        {"target": ""},
        {"target": "x" * 129},
        {"label": "yes"},
    ],
    ids=[
        "unknown_branch",
        "uppercase_branch",
        "empty_id",
        "long_id",
        "empty_source",
        "long_source",
        "empty_target",
        "long_target",
        "unknown_field",
    ],
)
def test_edge_rejects_invalid_fields(fields):
    values = {"id": "e", "source": "a", "target": "b", **fields}

    with pytest.raises(ValidationError):
        WorkflowEdge.model_validate(values)


def test_edge_may_point_at_its_own_source():
    edge = WorkflowEdge(id="loop", source="a", target="a")

    assert edge.source == edge.target


def test_graph_defaults_to_empty_collections():
    graph = WorkflowGraph()

    assert graph.nodes == []
    assert graph.edges == []
    assert graph.comments == []


def test_graph_caps_nodes_at_200():
    nodes = [{**node_values({"kind": "detect"}), "id": f"n{index}"} for index in range(201)]

    with pytest.raises(ValidationError, match="at most 200"):
        WorkflowGraph(nodes=nodes)


def test_graph_caps_edges_at_400():
    edges = [{"id": f"e{index}", "source": "a", "target": "b"} for index in range(401)]

    with pytest.raises(ValidationError, match="at most 400"):
        WorkflowGraph(edges=edges)


def test_graph_caps_comments_at_100():
    comments = [{"id": f"c{index}", "position": {"x": 0, "y": 0}} for index in range(101)]

    with pytest.raises(ValidationError, match="at most 100"):
        WorkflowGraph(comments=comments)


def test_graph_does_not_check_edge_endpoints():
    edges = [WorkflowEdge(id="e", source="ghost", target="phantom")]

    graph = WorkflowGraph(edges=edges)

    assert graph.edges == edges


def test_graph_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        WorkflowGraph(viewport={})


def test_graph_round_trips_through_json():
    zone = ZoneFilterData(polygon=[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0)])
    graph = WorkflowGraph(
        nodes=[WorkflowNode(id="n1", position=NodePosition(x=10.0, y=20.0), data=zone)],
        edges=[WorkflowEdge(id="e", source="n1", target="n1", branch="else")],
        comments=[CanvasComment(id="c1", position=NodePosition(x=0.0, y=0.0), text="hi")],
    )

    restored = WorkflowGraph.model_validate_json(graph.model_dump_json())

    assert restored == graph
    assert type(restored.nodes[0].data) is ZoneFilterData
