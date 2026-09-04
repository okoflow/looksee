from unittest.mock import AsyncMock

import httpx
import pytest

from api.adapters.persistence.db import get_session
from api.adapters.redis.rate_limits import RedisRateLimiter
from api.application import workflows
from api.entrypoints.http.dependencies import get_model_catalog, get_rate_limiter
from api.main import app


@pytest.fixture
async def http_client(postgres_sessions, valkey, catalog, monkeypatch):
    async def session():
        async with postgres_sessions() as connection:
            yield connection

    monkeypatch.setattr(workflows, "apply_camera_runtime_plan", AsyncMock())
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_session] = session
    app.dependency_overrides[get_model_catalog] = lambda: catalog
    app.dependency_overrides[get_rate_limiter] = lambda: RedisRateLimiter(valkey)

    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        await valkey.delete("looksee:rate:auth:127.0.0.1", "looksee:rate:auth:all")


async def test_authenticated_workflow_and_credentials_lifecycle(http_client, basic_graph):
    client = http_client
    owner = {"email": "owner@example.com", "name": "Owner", "password": "Secret123"}

    assert (await client.get("/workflows")).status_code == 401
    assert (await client.post("/auth/setup", json=owner)).status_code == 201
    assert (await client.get("/auth/me")).json()["email"] == owner["email"]

    created = await client.post(
        "/workflows",
        json={"name": "Integration", "graph": basic_graph.model_dump(mode="json")},
    )
    assert created.status_code == 201
    workflow_id = created.json()["id"]
    camera_id = created.json()["cameras"][0]["id"]

    enabled = await client.patch(f"/workflows/{workflow_id}", json={"enabled": True})

    assert enabled.status_code == 200
    assert enabled.json()["enabled"]
    assert enabled.json()["cameras"][0]["id"] == camera_id

    issued = await client.post(f"/cameras/{camera_id}/media-access", json={"action": "read"})
    allowed = await client.post(
        "/internal/media/auth",
        json={
            "action": "read",
            "path": camera_id,
            "token": issued.json()["token"],
            "protocol": "webrtc",
            "ip": "203.0.113.1",
        },
    )

    assert issued.status_code == 200
    assert allowed.status_code == 204

    credential = await client.post(
        "/credentials",
        json={
            "name": "Bot",
            "type": "telegram_bot",
            "payload": {"bot_token": "123:private-token"},
        },
    )

    assert credential.status_code == 201
    assert "private-token" not in credential.text
    listed = await client.get("/credentials")
    assert "private-token" not in listed.text
    credential_id = credential.json()["id"]

    stopped = await client.patch(f"/workflows/{workflow_id}", json={"enabled": False})

    assert stopped.status_code == 200
    assert not stopped.json()["enabled"]
    assert (await client.delete(f"/workflows/{workflow_id}")).status_code == 204
    assert (await client.get(f"/workflows/{workflow_id}")).status_code == 404
    assert (await client.delete(f"/credentials/{credential_id}")).status_code == 204

    assert (await client.post("/auth/logout")).status_code == 204
    assert (await client.get("/auth/me")).status_code == 401
    assert (
        await client.post(
            "/auth/login",
            json={
                "email": owner["email"],
                "password": owner["password"],
            },
        )
    ).status_code == 200
