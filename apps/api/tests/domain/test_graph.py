"""WorkflowGraphIndex: construction, adjacency, reachability, detect selection."""

from dataclasses import FrozenInstanceError

import pytest

from api.domain.errors import GraphErrorCode, WorkflowGraphError
from api.domain.graph import SelectedDetect, WorkflowGraphIndex
from api.domain.workflow import CameraSourceData, DetectData, WorkflowEdge, WorkflowGraph
from api.domain.workflow.actions import LogAlertActionData
from api.domain.workflow.filters import ClassFilterData
from api.domain.workflow.nodes import NodePosition, WorkflowNode

ORIGIN = NodePosition(x=0.0, y=0.0)


def node(node_id, data):
    return WorkflowNode(id=node_id, position=ORIGIN, data=data)


def edge(source, target, branch=None):
    return WorkflowEdge(id=f"{source}->{target}", source=source, target=target, branch=branch)


def build(nodes, edges):
    return WorkflowGraphIndex.build(WorkflowGraph(nodes=nodes, edges=edges))


@pytest.fixture
def linear_index():
    nodes = [
        node("cam", CameraSourceData()),
        node("detect", DetectData(model_id="yolo")),
        node("filter", ClassFilterData(classes=["person"])),
        node("alert", LogAlertActionData()),
    ]
    edges = [
        edge("cam", "detect"),
        edge("detect", "filter"),
        edge("filter", "alert", branch="if"),
    ]

    return build(nodes, edges)


def test_empty_graph_builds():
    index = WorkflowGraphIndex.build(WorkflowGraph())

    assert index.nodes_by_id == {}
    assert index.adjacency == {}
    assert index.source_nodes() == {}


def test_nodes_are_indexed_by_id(linear_index):
    assert set(linear_index.nodes_by_id) == {"cam", "detect", "filter", "alert"}
    assert isinstance(linear_index.nodes_by_id["detect"], DetectData)


def test_adjacency_lists_targets_in_edge_order(linear_index):
    expected = {"cam": ("detect",), "detect": ("filter",), "filter": ("alert",)}

    assert linear_index.adjacency == expected


def test_reverse_adjacency_lists_sources(linear_index):
    expected = {"detect": ("cam",), "filter": ("detect",), "alert": ("filter",)}

    assert linear_index.reverse_adjacency == expected


def test_outgoing_edges_are_grouped_by_source(linear_index):
    edges = linear_index.outgoing_edges["filter"]

    assert [item.id for item in edges] == ["filter->alert"]
    assert edges[0].branch == "if"


def test_fan_out_keeps_edge_order():
    nodes = [node("cam", CameraSourceData()), node("b", DetectData()), node("a", DetectData())]
    edges = [edge("cam", "b"), edge("cam", "a")]

    index = build(nodes, edges)

    assert index.adjacency["cam"] == ("b", "a")
    assert index.reverse_adjacency == {"b": ("cam",), "a": ("cam",)}


def test_isolated_nodes_are_absent_from_adjacency_maps():
    nodes = [node("cam", CameraSourceData()), node("alert", LogAlertActionData())]

    index = build(nodes, [])

    assert index.adjacency == {}
    assert index.reverse_adjacency == {}
    assert index.outgoing_edges == {}
    assert set(index.nodes_by_id) == {"cam", "alert"}


def test_source_nodes_returns_only_camera_sources(linear_index):
    sources = linear_index.source_nodes()

    assert list(sources) == ["cam"]
    assert isinstance(sources["cam"], CameraSourceData)


def test_duplicate_node_ids_are_reported_sorted():
    nodes = [
        node("b", DetectData()),
        node("a", DetectData()),
        node("b", DetectData()),
        node("a", DetectData()),
    ]

    with pytest.raises(WorkflowGraphError) as excinfo:
        build(nodes, [])

    assert excinfo.value.code is GraphErrorCode.DUPLICATE_NODE_IDS
    assert str(excinfo.value) == "duplicate node ids: a, b"


def test_duplicate_edge_id_is_rejected():
    nodes = [node("cam", CameraSourceData()), node("detect", DetectData())]
    edges = [
        WorkflowEdge(id="e", source="cam", target="detect"),
        WorkflowEdge(id="e", source="cam", target="detect"),
    ]

    with pytest.raises(WorkflowGraphError) as excinfo:
        build(nodes, edges)

    assert excinfo.value.code is GraphErrorCode.DUPLICATE_EDGE_ID
    assert str(excinfo.value) == "duplicate edge id: e"


@pytest.mark.parametrize(
    ("source", "target"),
    [("ghost", "detect"), ("cam", "ghost")],
    ids=["missing_source", "missing_target"],
)
def test_dangling_edge_is_rejected(source, target):
    nodes = [node("cam", CameraSourceData()), node("detect", DetectData())]

    with pytest.raises(WorkflowGraphError) as excinfo:
        build(nodes, [edge(source, target)])

    assert excinfo.value.code is GraphErrorCode.EDGE_NODE_MISSING
    assert f"'{source}->{target}'" in str(excinfo.value)


@pytest.mark.parametrize(
    "data",
    [CameraSourceData(), DetectData(), LogAlertActionData()],
    ids=["camera_source", "detect", "action"],
)
def test_branch_label_requires_a_filter_source(data):
    nodes = [node("src", data), node("alert", LogAlertActionData())]

    with pytest.raises(WorkflowGraphError) as excinfo:
        build(nodes, [edge("src", "alert", branch="else")])

    assert excinfo.value.code is GraphErrorCode.BRANCH_ON_NON_FILTER
    assert "'else'" in str(excinfo.value)


def test_branch_labels_are_allowed_on_filter_sources():
    nodes = [
        node("filter", ClassFilterData()),
        node("a", LogAlertActionData()),
        node("b", LogAlertActionData()),
    ]
    edges = [edge("filter", "a", branch="if"), edge("filter", "b", branch="else")]

    index = build(nodes, edges)

    assert index.adjacency["filter"] == ("a", "b")


def test_reachable_from_is_transitive_and_excludes_the_start(linear_index):
    assert linear_index.reachable_from("cam") == {"detect", "filter", "alert"}
    assert linear_index.reachable_from("filter") == {"alert"}
    assert linear_index.reachable_from("alert") == set()


def test_reachable_from_unknown_node_is_empty(linear_index):
    assert linear_index.reachable_from("ghost") == set()


def test_ancestors_walk_edges_backwards(linear_index):
    assert linear_index.ancestors_of("alert") == {"filter", "detect", "cam"}
    assert linear_index.ancestors_of("detect") == {"cam"}
    assert linear_index.ancestors_of("cam") == set()


def test_diamond_paths_visit_each_node_once():
    nodes = [
        node("cam", CameraSourceData()),
        node("a", ClassFilterData()),
        node("b", ClassFilterData()),
        node("alert", LogAlertActionData()),
    ]
    edges = [edge("cam", "a"), edge("cam", "b"), edge("a", "alert"), edge("b", "alert")]

    index = build(nodes, edges)

    assert index.reachable_from("cam") == {"a", "b", "alert"}
    assert index.ancestors_of("alert") == {"a", "b", "cam"}


def test_cycles_terminate_and_make_the_start_reachable_from_itself():
    nodes = [
        node("a", ClassFilterData()),
        node("b", ClassFilterData()),
        node("c", ClassFilterData()),
    ]
    edges = [edge("a", "b"), edge("b", "c"), edge("c", "a")]

    index = build(nodes, edges)

    assert index.reachable_from("a") == {"a", "b", "c"}
    assert index.ancestors_of("a") == {"a", "b", "c"}


def test_self_loop_is_accepted_by_build():
    nodes = [node("a", ClassFilterData())]

    index = build(nodes, [edge("a", "a")])

    assert index.reachable_from("a") == {"a"}


def test_detect_for_source_is_none_without_a_detect_node():
    nodes = [node("cam", CameraSourceData()), node("alert", LogAlertActionData())]

    index = build(nodes, [edge("cam", "alert")])

    assert index.detect_for_source("cam") is None


def test_detect_for_source_finds_the_downstream_detect(linear_index):
    detect_node_id, detect = linear_index.detect_for_source("cam")

    assert detect_node_id == "detect"
    assert detect.model_id == "yolo"


def test_detect_for_source_ignores_detect_nodes_of_other_sources():
    detect = DetectData(model_id="yolo")
    nodes = [
        node("cam", CameraSourceData()),
        node("detect", detect),
        node("other-cam", CameraSourceData()),
        node("other-detect", DetectData()),
    ]
    edges = [edge("cam", "detect"), edge("other-cam", "other-detect")]

    index = build(nodes, edges)

    assert index.detect_for_source("cam") == ("detect", detect)


def test_detect_for_source_ignores_upstream_detect_nodes():
    nodes = [node("detect", DetectData()), node("cam", CameraSourceData())]

    index = build(nodes, [edge("detect", "cam")])

    assert index.detect_for_source("cam") is None


def test_multiple_reachable_detect_nodes_are_rejected():
    nodes = [node("cam", CameraSourceData()), node("d2", DetectData()), node("d1", DetectData())]
    edges = [edge("cam", "d2"), edge("cam", "d1")]
    index = build(nodes, edges)

    with pytest.raises(WorkflowGraphError) as excinfo:
        index.detect_for_source("cam")

    assert excinfo.value.code is GraphErrorCode.MULTIPLE_DETECT_NODES
    assert excinfo.value.node_id == "cam"
    assert str(excinfo.value).endswith(": d1, d2")


def test_selected_detect_requires_a_detect_node():
    index = build([node("cam", CameraSourceData())], [])

    with pytest.raises(WorkflowGraphError) as excinfo:
        index.selected_detect_for_source("cam")

    assert excinfo.value.code is GraphErrorCode.DETECT_NODE_MISSING
    assert excinfo.value.node_id == "cam"


def test_selected_detect_requires_a_model():
    nodes = [node("cam", CameraSourceData()), node("detect", DetectData())]
    index = build(nodes, [edge("cam", "detect")])

    with pytest.raises(WorkflowGraphError) as excinfo:
        index.selected_detect_for_source("cam")

    assert excinfo.value.code is GraphErrorCode.MODEL_NOT_SELECTED
    assert excinfo.value.node_id == "detect"


def test_selected_detect_carries_node_model_and_data(linear_index):
    selected = linear_index.selected_detect_for_source("cam")

    expected = SelectedDetect(node_id="detect", model_id="yolo", data=DetectData(model_id="yolo"))

    assert selected == expected


def test_index_is_immutable(linear_index):
    with pytest.raises(FrozenInstanceError):
        linear_index.adjacency = {}


def test_selected_detect_is_immutable(linear_index):
    selected = linear_index.selected_detect_for_source("cam")

    with pytest.raises(FrozenInstanceError):
        selected.model_id = "other"
