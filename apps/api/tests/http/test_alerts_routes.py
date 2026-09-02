"""Alert listing and deletion over HTTP."""

from uuid import uuid4

import pytest

from api.adapters.persistence.models import Alert
from api.domain.enums import AlertSeverity


@pytest.fixture
def alerts(fake_session, owner):
    camera_a, camera_b = uuid4(), uuid4()
    rows = [
        Alert(camera_id=camera_a, kind="A", severity=AlertSeverity.INFO, message="1"),
        Alert(camera_id=camera_a, kind="B", severity=AlertSeverity.CRITICAL, message="2"),
        Alert(camera_id=camera_b, kind="C", severity=AlertSeverity.WARNING, message="3"),
    ]
    fake_session.seed(*rows)

    return {"camera_a": camera_a, "rows": rows}


def test_list_returns_alert_documents(client, alerts):
    response = client.get("/alerts")

    body = response.json()
    assert response.status_code == 200
    assert len(body) == 3
    assert set(body[0]) == {
        "id",
        "workflow_id",
        "camera_id",
        "kind",
        "severity",
        "message",
        "payload",
        "created_at",
    }
    assert body[0]["payload"] == {}


def test_list_filters_by_camera_and_severity(client, alerts):
    by_camera = client.get("/alerts", params={"camera_id": str(alerts["camera_a"])}).json()
    critical = client.get("/alerts", params={"severity": "critical"}).json()

    assert sorted(a["message"] for a in by_camera) == ["1", "2"]
    assert [a["message"] for a in critical] == ["2"]


@pytest.mark.parametrize(
    "params", [{"limit": 0}, {"limit": 501}, {"severity": "loud"}, {"camera_id": "x"}]
)
def test_list_validates_query_parameters(client, owner, params):
    assert client.get("/alerts", params=params).status_code == 422


def test_delete_one_alert(client, alerts):
    target = alerts["rows"][0]

    assert client.delete(f"/alerts/{target.id}").status_code == 204
    assert client.delete(f"/alerts/{target.id}").status_code == 404


def test_clear_scoped_to_a_camera(client, alerts):
    response = client.delete("/alerts", params={"camera_id": str(alerts["camera_a"])})

    assert response.status_code == 204
    assert [a["message"] for a in client.get("/alerts").json()] == ["3"]
