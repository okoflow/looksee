import pytest

from api.adapters.persistence.models import Camera, Workflow
from api.domain.enums import CameraSource


def test_untrusted_origin_cannot_create_owner(client):
    response = client.post(
        "/auth/setup",
        headers={"Origin": "https://untrusted.example"},
        json={"email": "owner@example.com", "name": "Owner", "password": "Secret123"},
    )

    assert response.status_code == 403
    assert client.get("/auth/status").json()["requires_setup"]


@pytest.mark.parametrize("origin", ["http://testserver", "http://localhost:3000"])
def test_allowed_origin_can_sign_in(client, origin):
    response = client.post(
        "/auth/setup",
        headers={"Origin": origin},
        json={"email": "owner@example.com", "name": "Owner", "password": "Secret123"},
    )

    assert response.status_code == 201


def test_validation_errors_do_not_echo_passwords(client):
    response = client.post(
        "/auth/setup",
        json={"email": "owner@example.com", "name": "Owner", "password": "bad"},
    )

    assert response.status_code == 422
    assert all(set(error) == {"type", "loc", "msg"} for error in response.json()["detail"])
    assert '"input"' not in response.text


def test_auth_rate_limit_returns_retry_after(client, rate_limiter):
    rate_limiter.counts["auth:testclient"] = 20

    response = client.post(
        "/auth/login",
        json={"email": "owner@example.com", "password": "Secret123"},
    )

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "60"


def test_media_token_endpoint_requires_an_authenticated_user(client):
    response = client.post(
        "/cameras/00000000-0000-0000-0000-000000000001/media-access",
        json={"action": "read"},
    )

    assert response.status_code == 401


def test_media_grant_works_with_actual_callback_contract(client, owner, fake_session, basic_graph):
    workflow = Workflow(name="Media", graph=basic_graph.model_dump(mode="json"))
    fake_session.seed(workflow)
    camera = Camera(
        workflow_id=workflow.id,
        node_id="cam",
        name="Webcam",
        source_type=CameraSource.WEBRTC,
    )
    fake_session.seed(camera)

    issued = client.post(f"/cameras/{camera.id}/media-access", json={"action": "read"})
    response = client.post(
        "/internal/media/auth",
        json={
            "action": "read",
            "path": str(camera.id),
            "token": issued.json()["token"],
            "ip": "203.0.113.1",
            "protocol": "webrtc",
            "id": "connection",
            "query": "",
        },
    )

    assert issued.headers["Cache-Control"] == "no-store"
    assert response.status_code == 204
