"""Action dispatch by payload type, including registered commercial actions."""

from typing import Literal, get_args

import pytest

from api.adapters.actions import dispatcher
from api.domain.workflow import ActionData, ActionNodeData, LogAlertActionData, WebhookActionData
from api.domain.workflow.extensions import NODE_EXTENSIONS


def test_every_built_in_action_has_a_handler():
    assert set(get_args(ActionData)) <= set(dispatcher._HANDLERS)


def test_extension_actions_dispatch_to_their_own_deliverer():
    action_extensions = [e for e in NODE_EXTENSIONS if issubclass(e.draft, ActionNodeData)]

    for extension in action_extensions:
        assert dispatcher._HANDLERS[extension.draft] is dispatcher._load_handler(extension.deliver)


async def test_dispatch_selects_the_handler_for_the_payload_type(monkeypatch, identity, make_event):
    calls = []

    async def fake_alert(identity, event, action, context):
        calls.append(("alert", action, context))

    async def fake_webhook(identity, event, action, context):
        calls.append(("webhook", action, context))

    monkeypatch.setitem(dispatcher._HANDLERS, LogAlertActionData, fake_alert)
    monkeypatch.setitem(dispatcher._HANDLERS, WebhookActionData, fake_webhook)
    alert = LogAlertActionData(cooldown_seconds=5)
    context = {"snapshot_url": "/snapshots/a.jpg"}

    await dispatcher.dispatch_action(identity, make_event(), alert, context)

    assert calls == [("alert", alert, context)]


async def test_unregistered_action_type_is_a_programming_error(identity, make_event):
    class RogueAction(ActionNodeData):
        kind: Literal["rogue_action"] = "rogue_action"

    with pytest.raises(KeyError):
        await dispatcher.dispatch_action(identity, make_event(), RogueAction(), {})
