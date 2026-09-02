"""How the ee distribution plugs into the core node registry and entitlements."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from api.adapters.actions import dispatcher
from api.application import entitlements as core_entitlements
from api.domain.errors import GraphErrorCode, WorkflowGraphError
from api.domain.workflow import LICENSED_FEATURES_BY_KIND, WorkflowGraph, ensure_node_runnable
from api.domain.workflow import extensions as core_extensions
from ee.adapters.delivery import run_slack
from ee.features import ALL_FEATURES, ENTERPRISE_INTEGRATIONS, MEASUREMENT_FILTERS
from ee.license import resolve_entitlements
from ee.workflow import NODE_EXTENSIONS
from ee.workflow.actions import RunnableSlackAction, SlackActionData
from ee.workflow.filters import DwellFilterData, LineCrossingFilterData


def test_core_registry_is_the_ee_extension_tuple():
    assert core_extensions.NODE_EXTENSIONS is NODE_EXTENSIONS


def test_every_extension_declares_kind_feature_and_models():
    assert {(e.kind, e.feature) for e in NODE_EXTENSIONS} == {
        ("line_crossing_filter", MEASUREMENT_FILTERS),
        ("dwell_filter", MEASUREMENT_FILTERS),
        ("count_threshold_filter", MEASUREMENT_FILTERS),
        ("slack_action", ENTERPRISE_INTEGRATIONS),
    }
    for extension in NODE_EXTENSIONS:
        assert extension.draft.model_fields["kind"].default == extension.kind
        assert issubclass(extension.runnable, extension.draft)


def test_licensed_features_are_indexed_by_node_kind():
    assert {e.kind: e.feature for e in NODE_EXTENSIONS} == LICENSED_FEATURES_BY_KIND


def test_extension_nodes_parse_inside_a_workflow_graph():
    graph = WorkflowGraph.model_validate(
        {
            "nodes": [
                {
                    "id": "a",
                    "position": {"x": 0, "y": 0},
                    "data": {"kind": "slack_action", "credential_id": str(uuid4())},
                },
                {
                    "id": "b",
                    "position": {"x": 0, "y": 0},
                    "data": {"kind": "dwell_filter", "polygon": [[0, 0], [1, 0], [1, 1]]},
                },
            ]
        }
    )

    assert isinstance(graph.nodes[0].data, SlackActionData)
    assert isinstance(graph.nodes[1].data, DwellFilterData)


@pytest.mark.parametrize(
    ("data", "field"),
    [
        (LineCrossingFilterData(line=[(0.1, 0.1)]), "line"),
        (DwellFilterData(polygon=[(0, 0), (1, 1)]), "polygon"),
        (SlackActionData(credential_id=""), "credential_id"),
    ],
)
def test_runnable_refinements_gate_incomplete_extension_nodes(data, field):
    with pytest.raises(WorkflowGraphError) as excinfo:
        ensure_node_runnable("n", data)

    assert excinfo.value.code is GraphErrorCode.NODE_NOT_RUNNABLE
    assert field in str(excinfo.value)


def test_complete_extension_nodes_are_runnable():
    ensure_node_runnable("a", LineCrossingFilterData(line=[(0.1, 0.5), (0.9, 0.5)]))
    ensure_node_runnable("b", DwellFilterData(polygon=[(0, 0), (1, 0), (1, 1)]))
    ensure_node_runnable("c", SlackActionData(credential_id=str(uuid4())))


def test_runnable_slack_action_requires_a_uuid_credential():
    with pytest.raises(ValidationError):
        RunnableSlackAction(credential_id="not-a-uuid")


def test_slack_action_declares_its_credential_type():
    assert SlackActionData.credential_type == "slack_webhook"


def test_slack_delivery_is_registered_with_the_core_dispatcher():
    assert dispatcher._HANDLERS[SlackActionData] is run_slack


def test_missing_license_key_is_community():
    assert resolve_entitlements(None) is core_entitlements.COMMUNITY_ENTITLEMENTS


def test_any_license_key_unlocks_every_feature():
    entitlements = resolve_entitlements("LS-TRIAL")

    assert entitlements.edition == "enterprise"
    assert entitlements.features == ALL_FEATURES
    assert entitlements.allows(MEASUREMENT_FILTERS) and entitlements.allows(ENTERPRISE_INTEGRATIONS)


def test_core_entitlement_resolution_delegates_to_ee():
    assert core_entitlements.resolve_entitlements("LS-TRIAL").edition == "enterprise"
    assert core_entitlements.resolve_entitlements(None).edition == "community"
