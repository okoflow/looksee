"""Commercial node extension registry."""

import sys
import typing
from dataclasses import FrozenInstanceError

import pytest

from api.domain.workflow import extensions
from api.domain.workflow.actions import ActionNodeData
from api.domain.workflow.base import WorkflowModel
from api.domain.workflow.extensions import (
    LICENSED_FEATURES_BY_KIND,
    NODE_EXTENSIONS,
    NodeExtension,
)
from api.domain.workflow.filters import FilterNodeData
from api.domain.workflow.nodes import NodeDataUnion
from api.domain.workflow.runnable import RunnableNodeDataUnion


class Draft(WorkflowModel):
    kind: typing.Literal["sample_filter"] = "sample_filter"


def extension_id(extension):
    return extension.kind


def test_registry_is_an_immutable_tuple():
    assert isinstance(NODE_EXTENSIONS, tuple)


def test_extension_kinds_are_unique():
    kinds = [extension.kind for extension in NODE_EXTENSIONS]

    assert len(kinds) == len(set(kinds))


@pytest.mark.parametrize("extension", NODE_EXTENSIONS, ids=extension_id)
def test_extension_draft_declares_its_kind(extension):
    draft = extension.draft()

    assert draft.kind == extension.kind


@pytest.mark.parametrize("extension", NODE_EXTENSIONS, ids=extension_id)
def test_extension_runnable_refines_its_draft(extension):
    assert issubclass(extension.draft, WorkflowModel)
    assert issubclass(extension.runnable, extension.draft)


@pytest.mark.parametrize("extension", NODE_EXTENSIONS, ids=extension_id)
def test_extension_is_a_filter_or_an_action(extension):
    is_filter = issubclass(extension.draft, FilterNodeData)
    is_action = issubclass(extension.draft, ActionNodeData)

    assert is_filter != is_action


@pytest.mark.parametrize("extension", NODE_EXTENSIONS, ids=extension_id)
def test_only_action_extensions_carry_a_delivery_handler(extension):
    is_action = issubclass(extension.draft, ActionNodeData)

    assert (extension.deliver is not None) is is_action


@pytest.mark.parametrize("extension", NODE_EXTENSIONS, ids=extension_id)
def test_extension_models_join_both_node_unions(extension):
    assert extension.draft in typing.get_args(NodeDataUnion)
    assert extension.runnable in typing.get_args(RunnableNodeDataUnion)


def test_licensed_features_index_every_extension_kind():
    expected = {extension.kind: extension.feature for extension in NODE_EXTENSIONS}

    assert expected == LICENSED_FEATURES_BY_KIND


@pytest.mark.parametrize(
    "kind",
    ["camera_source", "detect", "if_else_filter", "class_filter", "log_alert_action"],
)
def test_builtin_kinds_need_no_license(kind):
    assert kind not in LICENSED_FEATURES_BY_KIND


def test_unknown_kind_has_no_feature():
    assert LICENSED_FEATURES_BY_KIND.get("teleport_action") is None


def test_commercial_kinds_are_registered_when_ee_is_installed():
    pytest.importorskip("ee.workflow")

    expected = {"line_crossing_filter", "dwell_filter", "count_threshold_filter", "slack_action"}

    assert expected <= set(LICENSED_FEATURES_BY_KIND)


def test_extension_defaults_to_no_delivery_handler():
    extension = NodeExtension(kind="sample_filter", feature="samples", draft=Draft, runnable=Draft)

    assert extension.deliver is None


def test_extension_is_frozen():
    extension = NodeExtension(kind="sample_filter", feature="samples", draft=Draft, runnable=Draft)

    with pytest.raises(FrozenInstanceError):
        extension.kind = "other"


def test_extension_has_no_instance_dict():
    extension = NodeExtension(kind="sample_filter", feature="samples", draft=Draft, runnable=Draft)

    assert not hasattr(extension, "__dict__")


def test_registry_is_empty_when_ee_is_absent(monkeypatch):
    monkeypatch.setitem(sys.modules, "ee.workflow", None)

    loaded = extensions._load_node_extensions()

    assert loaded == ()
