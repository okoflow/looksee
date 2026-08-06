"""Declarative dispatch of action nodes to their delivery adapters."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, get_args

from api.adapters.actions.alerts import run_log_alert
from api.adapters.actions.delivery import (
    run_discord,
    run_email,
    run_mqtt,
    run_telegram,
    run_webhook,
)
from api.adapters.actions.snapshots import run_snapshot
from api.domain.workflow import (
    ActionData,
    ActionNodeData,
    DiscordActionData,
    EmailActionData,
    LogAlertActionData,
    MqttActionData,
    SnapshotActionData,
    TelegramActionData,
    WebhookActionData,
)
from api.domain.workflow.extensions import NODE_EXTENSIONS

if TYPE_CHECKING:
    from api.application.execution import ExecutionIdentity
    from api.domain.events import DetectionEvent

type ActionHandler = Callable[
    ["ExecutionIdentity", "DetectionEvent", Any, dict[str, Any]],
    Awaitable[None],
]

_EXTENSION_HANDLERS: dict[type, ActionHandler] = {
    extension.draft: extension.deliver
    for extension in NODE_EXTENSIONS
    if extension.deliver is not None
}

_HANDLERS: dict[type, ActionHandler] = {
    LogAlertActionData: run_log_alert,
    WebhookActionData: run_webhook,
    TelegramActionData: run_telegram,
    SnapshotActionData: run_snapshot,
    EmailActionData: run_email,
    MqttActionData: run_mqtt,
    DiscordActionData: run_discord,
    **_EXTENSION_HANDLERS,
}

_UNHANDLED_ACTIONS = {
    *get_args(ActionData),
    *(
        extension.draft
        for extension in NODE_EXTENSIONS
        if issubclass(extension.draft, ActionNodeData)
    ),
} - set(_HANDLERS)
if _UNHANDLED_ACTIONS:
    names = ", ".join(sorted(action_type.__name__ for action_type in _UNHANDLED_ACTIONS))
    raise TypeError(f"action payloads without a delivery handler: {names}")


async def dispatch_action(
    identity: ExecutionIdentity,
    event: DetectionEvent,
    action: ActionNodeData,
    context: dict[str, Any],
) -> None:
    await _HANDLERS[type(action)](identity, event, action, context)
