"""Persist and broadcast the built-in alert action."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from api.adapters.actions.formatting import humanize_event_kind
from api.adapters.persistence.db import session_factory
from api.adapters.persistence.models import Alert
from api.adapters.realtime.broadcaster import broadcaster
from api.adapters.state.memory import runtime_state

if TYPE_CHECKING:
    from api.application.execution import ExecutionIdentity
    from api.domain.events import DetectionEvent
    from api.domain.workflow import LogAlertActionData


def _cooldown_active(identity: ExecutionIdentity, event: DetectionEvent, seconds: int) -> bool:
    if seconds == 0:
        return False

    return not runtime_state.debounce_allows(
        identity.workflow_id,
        identity.run_id,
        identity.node_id,
        event.camera_id,
        seconds,
    )


async def run_log_alert(
    identity: ExecutionIdentity,
    event: DetectionEvent,
    config: LogAlertActionData,
    context: dict[str, Any],
) -> None:
    if _cooldown_active(identity, event, config.cooldown_seconds):
        return
    payload: dict[str, Any] = {
        "ts": event.ts.isoformat(),
        "detections": [detection.model_dump(mode="json") for detection in event.detections],
        "metadata": dict(event.metadata),
    }
    if "snapshot_url" in context:
        payload["snapshot_url"] = context["snapshot_url"]

    async with session_factory() as session:
        alert = Alert(
            workflow_id=identity.workflow_id,
            camera_id=event.camera_id,
            kind=event.kind,
            severity=config.severity,
            message=f"{humanize_event_kind(event.kind)} on {identity.camera_name}",
            payload=payload,
        )
        session.add(alert)
        await session.commit()
        await session.refresh(alert)

    await broadcaster.publish(
        event.camera_id,
        {
            "type": "alert",
            "id": str(alert.id),
            "kind": alert.kind,
            "severity": alert.severity.value,
            "message": alert.message,
            "ts": alert.created_at.isoformat(),
            "snapshot_url": context.get("snapshot_url"),
        },
    )
