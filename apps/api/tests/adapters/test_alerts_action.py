"""The built-in alert action: persisted row, broadcast payload, per-node cooldown."""

from dataclasses import replace

from api.adapters.actions.alerts import run_log_alert
from api.adapters.persistence.models import Alert
from api.domain.enums import AlertSeverity
from api.domain.workflow import LogAlertActionData


async def test_alert_is_persisted_and_broadcast(effects, fake_session, identity, make_event):
    event = make_event()
    action_identity = replace(identity, node_id="alert")

    await run_log_alert(
        action_identity, event, LogAlertActionData(severity=AlertSeverity.CRITICAL), {}
    )

    alert = fake_session.rows[Alert][0]
    assert (alert.workflow_id, alert.camera_id) == (identity.workflow_id, event.camera_id)
    assert alert.kind == "PERSON_DETECTED"
    assert alert.severity is AlertSeverity.CRITICAL
    assert alert.message == "Person on Front door"
    assert alert.payload["ts"] == event.ts.isoformat()
    assert alert.payload["detections"][0]["label"] == "person"
    assert alert.payload["metadata"] == {"count": 1, "model_id": "people"}
    assert effects.realtime == [
        (
            event.camera_id,
            {
                "type": "alert",
                "id": str(alert.id),
                "kind": "PERSON_DETECTED",
                "severity": "critical",
                "message": "Person on Front door",
                "ts": alert.created_at.isoformat(),
                "snapshot_url": None,
            },
        )
    ]


async def test_snapshot_taken_earlier_is_attached(effects, fake_session, identity, make_event):
    context = {"snapshot_url": "/snapshots/a.jpg", "snapshot_jpeg": b"jpeg"}

    await run_log_alert(identity, make_event(), LogAlertActionData(), context)

    assert fake_session.rows[Alert][0].payload["snapshot_url"] == "/snapshots/a.jpg"
    assert "snapshot_jpeg" not in fake_session.rows[Alert][0].payload
    assert effects.realtime[0][1]["snapshot_url"] == "/snapshots/a.jpg"


async def test_repeats_within_cooldown_are_dropped_per_node(
    effects, fake_session, identity, make_event
):
    event = make_event()
    first_node = replace(identity, node_id="alert-1")
    second_node = replace(identity, node_id="alert-2")
    config = LogAlertActionData(cooldown_seconds=60)

    await run_log_alert(first_node, event, config, {})
    await run_log_alert(first_node, event, config, {})
    await run_log_alert(second_node, event, config, {})

    assert len(fake_session.rows[Alert]) == 2
    assert len(effects.realtime) == 2


async def test_zero_cooldown_records_every_event(effects, fake_session, identity, make_event):
    event = make_event()
    config = LogAlertActionData(cooldown_seconds=0)

    await run_log_alert(identity, event, config, {})
    await run_log_alert(identity, event, config, {})

    assert len(fake_session.rows[Alert]) == 2
