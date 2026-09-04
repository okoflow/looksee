"""Credential CRUD over HTTP; secrets go in and never come back."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

TELEGRAM = {"name": "bot", "type": "telegram_bot", "payload": {"bot_token": "123:secret"}}


@pytest.fixture
def created(client, owner):
    response = client.post("/credentials", json=TELEGRAM)
    assert response.status_code == 201

    return response.json()


def test_create_returns_metadata_but_never_the_secret(created):
    assert set(created) == {"id", "name", "type", "summary", "created_at", "updated_at"}
    assert created["summary"] == "Telegram bot"
    assert "secret" not in str(created)


def test_list_includes_the_credential(client, created):
    assert [c["id"] for c in client.get("/credentials").json()] == [created["id"]]


def test_duplicate_name_is_a_conflict(client, created):
    response = client.post("/credentials", json=TELEGRAM)

    assert response.status_code == 409
    assert response.json() == {"detail": "Credential named 'bot' already exists"}


def test_unknown_type_is_a_validation_error(client, owner):
    response = client.post("/credentials", json={**TELEGRAM, "type": "carrier_pigeon"})

    assert response.status_code == 422


def test_invalid_payload_is_a_validation_error(client, owner):
    lenient = TestClient(client.app, raise_server_exceptions=False, cookies=client.cookies)

    response = lenient.post("/credentials", json={**TELEGRAM, "payload": {"token": "wrong-key"}})

    assert response.status_code == 422


def test_rename_keeps_type_and_summary(client, created):
    response = client.patch(f"/credentials/{created['id']}", json={"name": "renamed"})

    assert response.status_code == 200
    assert response.json()["name"] == "renamed"
    assert response.json()["summary"] == "Telegram bot"


def test_update_of_unknown_credential_is_not_found(client, owner):
    response = client.patch(f"/credentials/{uuid4()}", json={"name": "x"})

    assert response.status_code == 404
    assert response.json() == {"detail": "credential not found"}


def test_delete_removes_the_credential(client, created):
    assert client.delete(f"/credentials/{created['id']}").status_code == 204
    assert client.delete(f"/credentials/{created['id']}").status_code == 404
    assert client.get("/credentials").json() == []
