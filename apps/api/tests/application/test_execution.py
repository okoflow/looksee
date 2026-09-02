"""Routing one detection event through a graph: detect gates, branches, actions."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from api.application.execution import execute_event
from api.domain.graph import WorkflowGraphIndex

UTC_ZONE = ZoneInfo("UTC")


class RecordingState:
    def __init__(self, allow=True):
        self.allow = allow
        self.debounce_calls = []

    def debounce_allows(self, workflow_id, run_id, node_id, camera_id, seconds):
        self.debounce_calls.append((workflow_id, run_id, node_id, camera_id, seconds))

        return self.allow

    def swap_track_point(self, *args):
        return None

    def dwell_seconds(self, *args):
        return 0.0


@pytest.fixture
def actions():
    return []


@pytest.fixture
def run_action(actions):
    async def _run(identity, event, action, context):
        actions.append((identity.node_id, action.kind, context))

    return _run


@pytest.fixture
def execute(build_graph, identity, make_event, run_action):
    async def _execute(nodes, edges, event=None, timezone=UTC_ZONE, state=None):
        index = WorkflowGraphIndex.build(build_graph(nodes, edges))
        await execute_event(
            index,
            "cam",
            identity,
            event if event is not None else make_event(),
            timezone,
            state if state is not None else RecordingState(),
            run_action,
        )

    return _execute


async def test_action_downstream_of_matching_detect_runs_once(execute, basic_nodes, actions):
    await execute(basic_nodes, [("cam", "det"), ("det", "alert")])

    assert [(node_id, kind) for node_id, kind, _ in actions] == [("alert", "log_alert_action")]


async def test_detect_event_kinds_gate_the_rest_of_the_graph(execute, basic_nodes, actions):
    basic_nodes["det"]["event_kinds"] = ["CAR_DETECTED"]

    await execute(basic_nodes, [("cam", "det"), ("det", "alert")])

    assert actions == []


async def test_if_else_routes_to_the_else_branch_when_condition_fails(
    execute, basic_nodes, actions
):
    basic_nodes["gate"] = {
        "kind": "if_else_filter",
        "condition": {"field": "detection_count", "operator": "gte", "value": 2},
    }
    basic_nodes["fallback"] = {"kind": "snapshot_action"}
    edges = [("cam", "det"), ("det", "gate"), ("gate", "alert", "if"), ("gate", "fallback", "else")]

    await execute(basic_nodes, edges)

    assert [node_id for node_id, _, _ in actions] == ["fallback"]


async def test_if_else_routes_to_the_if_branch_when_condition_holds(execute, basic_nodes, actions):
    basic_nodes["gate"] = {
        "kind": "if_else_filter",
        "condition": {"field": "object_class", "value": "person"},
    }
    basic_nodes["fallback"] = {"kind": "snapshot_action"}
    edges = [("cam", "det"), ("det", "gate"), ("gate", "alert", "if"), ("gate", "fallback", "else")]

    await execute(basic_nodes, edges)

    assert [node_id for node_id, _, _ in actions] == ["alert"]


async def test_unlabeled_edge_out_of_a_filter_follows_the_positive_branch(
    execute, basic_nodes, actions
):
    basic_nodes["gate"] = {"kind": "class_filter", "classes": ["person"]}
    edges = [("cam", "det"), ("det", "gate"), ("gate", "alert")]

    await execute(basic_nodes, edges)

    assert [node_id for node_id, _, _ in actions] == ["alert"]


async def test_action_reachable_along_two_paths_runs_once(execute, basic_nodes, actions):
    basic_nodes["gate"] = {"kind": "class_filter"}
    edges = [("cam", "det"), ("det", "alert"), ("det", "gate"), ("gate", "alert")]

    await execute(basic_nodes, edges)

    assert len(actions) == 1


async def test_failing_action_is_logged_and_others_still_run(
    build_graph, basic_nodes, identity, make_event, caplog
):
    basic_nodes["boom"] = {"kind": "snapshot_action"}
    index = WorkflowGraphIndex.build(
        build_graph(basic_nodes, [("cam", "det"), ("det", "boom"), ("det", "alert")])
    )
    ran = []

    async def run_action(identity, event, action, context):
        if action.kind == "snapshot_action":
            raise RuntimeError("no frame")
        ran.append(identity.node_id)

    await execute_event(
        index, "cam", identity, make_event(), UTC_ZONE, RecordingState(), run_action
    )

    assert ran == ["alert"]
    assert "action failed node=boom" in caplog.text


async def test_context_flows_from_earlier_to_later_actions(
    build_graph, basic_nodes, identity, make_event
):
    basic_nodes["snap"] = {"kind": "snapshot_action"}
    index = WorkflowGraphIndex.build(
        build_graph(basic_nodes, [("cam", "det"), ("det", "snap"), ("det", "alert")])
    )
    seen = {}

    async def run_action(identity, event, action, context):
        if action.kind == "snapshot_action":
            context["snapshot_url"] = "/snapshots/a.jpg"
        else:
            seen.update(context)

    await execute_event(
        index, "cam", identity, make_event(), UTC_ZONE, RecordingState(), run_action
    )

    assert seen == {"snapshot_url": "/snapshots/a.jpg"}


async def test_unknown_source_node_executes_nothing(
    build_graph, basic_nodes, identity, make_event, actions, run_action
):
    index = WorkflowGraphIndex.build(build_graph(basic_nodes, [("cam", "det"), ("det", "alert")]))

    await execute_event(
        index, "ghost", identity, make_event(), UTC_ZONE, RecordingState(), run_action
    )

    assert actions == []


@pytest.mark.parametrize(
    ("timezone", "expected_nodes"),
    [
        (ZoneInfo("America/New_York"), ["alert"]),
        (ZoneInfo("UTC"), []),
    ],
)
async def test_time_window_is_evaluated_in_the_configured_timezone(
    execute, basic_nodes, make_event, actions, timezone, expected_nodes
):
    basic_nodes["hours"] = {
        "kind": "time_window_filter",
        "start_hour": 9,
        "end_hour": 20,
        "weekdays": [0, 1, 2, 3, 4, 5, 6],
    }
    late_evening_utc = make_event(ts=datetime(2026, 3, 4, 23, 30, tzinfo=UTC))

    await execute(
        basic_nodes,
        [("cam", "det"), ("det", "hours"), ("hours", "alert")],
        event=late_evening_utc,
        timezone=timezone,
    )

    assert [node_id for node_id, _, _ in actions] == expected_nodes


async def test_debounce_filter_consults_runtime_state_with_node_identity(
    execute, basic_nodes, identity, make_event, actions
):
    basic_nodes["deb"] = {"kind": "debounce_filter", "seconds": 45}
    state = RecordingState(allow=False)
    event = make_event()

    await execute(
        basic_nodes, [("cam", "det"), ("det", "deb"), ("deb", "alert")], event=event, state=state
    )

    assert actions == []
    assert state.debounce_calls == [
        (identity.workflow_id, identity.run_id, "deb", event.camera_id, 45)
    ]


async def test_identity_handed_to_actions_carries_their_node_id(
    build_graph, basic_nodes, identity, make_event
):
    index = WorkflowGraphIndex.build(build_graph(basic_nodes, [("cam", "det"), ("det", "alert")]))
    identities = []

    async def run_action(action_identity, event, action, context):
        identities.append(action_identity)

    await execute_event(
        index, "cam", identity, make_event(), UTC_ZONE, RecordingState(), run_action
    )

    assert identities[0].node_id == "alert"
    assert identities[0].workflow_id == identity.workflow_id
    assert identities[0].camera_name == "Front door"
    assert identity.node_id == ""
