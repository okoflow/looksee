"""Public surface of the workflow package."""

import pytest

from api.domain import workflow
from api.domain.workflow import runnable


def test_every_exported_name_resolves():
    for name in workflow.__all__:
        assert hasattr(workflow, name)


def test_exports_are_unique():
    assert len(workflow.__all__) == len(set(workflow.__all__))


def test_exports_the_runnable_entry_point():
    assert workflow.ensure_node_runnable is runnable.ensure_node_runnable


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("CameraSourceData", "camera_source"),
        ("DetectData", "detect"),
        ("IfElseFilterData", "if_else_filter"),
        ("ClassFilterData", "class_filter"),
        ("LogAlertActionData", "log_alert_action"),
        ("SnapshotActionData", "snapshot_action"),
        ("TelegramActionData", "telegram_action"),
        ("WebhookActionData", "webhook_action"),
        ("EmailActionData", "email_action"),
        ("MqttActionData", "mqtt_action"),
        ("DiscordActionData", "discord_action"),
    ],
)
def test_exports_node_payloads_by_kind(name, kind):
    node_type = getattr(workflow, name)

    assert node_type.model_fields["kind"].default == kind


def test_exports_the_dispatch_bases():
    assert issubclass(workflow.ClassFilterData, workflow.FilterNodeData)
    assert issubclass(workflow.LogAlertActionData, workflow.ActionNodeData)
