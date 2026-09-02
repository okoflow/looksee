"""Alert listing, deletion, and scoped clearing."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from api.adapters.persistence.models import Alert
from api.application import alerts
from api.application.errors import ResourceNotFoundError
from api.domain.enums import AlertSeverity


@pytest.fixture
def seeded(fake_session):
    camera_a, camera_b, workflow = uuid4(), uuid4(), uuid4()
    base = datetime(2026, 3, 4, tzinfo=UTC)
    rows = [
        Alert(
            camera_id=camera_a,
            workflow_id=workflow,
            kind="A",
            severity=AlertSeverity.INFO,
            message="1",
        ),
        Alert(
            camera_id=camera_a,
            workflow_id=workflow,
            kind="B",
            severity=AlertSeverity.CRITICAL,
            message="2",
        ),
        Alert(
            camera_id=camera_b,
            workflow_id=workflow,
            kind="C",
            severity=AlertSeverity.WARNING,
            message="3",
        ),
        Alert(
            camera_id=camera_b,
            workflow_id=uuid4(),
            kind="D",
            severity=AlertSeverity.INFO,
            message="4",
        ),
    ]
    fake_session.seed(*rows)
    for offset, row in enumerate(rows):
        row.created_at = base + timedelta(minutes=offset)

    return {"camera_a": camera_a, "camera_b": camera_b, "workflow": workflow, "rows": rows}


async def list_messages(fake_session, **filters):
    arguments = {"camera_id": None, "workflow_id": None, "severity": None, "limit": 100}
    arguments.update(filters)
    listed = await alerts.list_alerts(fake_session, **arguments)

    return [alert.message for alert in listed]


async def test_list_returns_newest_first(fake_session, seeded):
    assert await list_messages(fake_session) == ["4", "3", "2", "1"]


async def test_list_filters_by_camera_workflow_and_severity(fake_session, seeded):
    by_camera = await list_messages(fake_session, camera_id=seeded["camera_a"])
    by_workflow = await list_messages(fake_session, workflow_id=seeded["workflow"])
    by_severity = await list_messages(fake_session, severity=AlertSeverity.INFO)
    combined = await list_messages(
        fake_session, camera_id=seeded["camera_b"], workflow_id=seeded["workflow"]
    )

    assert by_camera == ["2", "1"]
    assert by_workflow == ["3", "2", "1"]
    assert by_severity == ["4", "1"]
    assert combined == ["3"]


async def test_list_honours_the_limit(fake_session, seeded):
    assert await list_messages(fake_session, limit=2) == ["4", "3"]


async def test_delete_removes_one_alert(fake_session, seeded):
    target = seeded["rows"][0]

    await alerts.delete_alert(fake_session, target.id)

    assert target not in fake_session.rows[Alert]
    assert fake_session.commits == 1


async def test_delete_unknown_alert_raises_not_found(fake_session):
    with pytest.raises(ResourceNotFoundError, match="alert not found"):
        await alerts.delete_alert(fake_session, uuid4())


async def test_clear_is_scoped_by_camera_and_workflow(fake_session, seeded):
    await alerts.clear_alerts(
        fake_session, camera_id=seeded["camera_b"], workflow_id=seeded["workflow"]
    )

    assert await list_messages(fake_session) == ["4", "2", "1"]


async def test_clear_without_scope_removes_everything(fake_session, seeded):
    await alerts.clear_alerts(fake_session, camera_id=None, workflow_id=None)

    assert fake_session.rows[Alert] == []
