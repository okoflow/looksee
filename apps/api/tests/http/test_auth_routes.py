"""First-run setup, login, logout, and session cookie handling."""

import pytest

from api.entrypoints.http.dependencies import SESSION_COOKIE


def test_status_reports_setup_until_the_owner_exists(client, owner):
    assert client.get("/auth/status").json() == {"requires_setup": False}


def test_fresh_instance_requires_setup(client):
    assert client.get("/auth/status").json() == {"requires_setup": True}


def test_setup_creates_the_owner_and_opens_a_session(client):
    response = client.post(
        "/auth/setup", json={"email": "Owner@Example.com", "name": "Owner", "password": "Secret123"}
    )

    cookie = response.headers["set-cookie"].lower()
    body = response.json()
    assert response.status_code == 201
    assert set(body) == {"id", "email", "name", "role", "created_at"}
    assert body["email"] == "owner@example.com"
    assert body["role"] == "owner"
    assert f"{SESSION_COOKIE}=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert "path=/" in cookie
    assert "max-age=604800" in cookie
    assert "secure" not in cookie
    assert client.get("/auth/me").json()["email"] == "owner@example.com"


def test_setup_is_refused_once_an_owner_exists(client, owner):
    response = client.post(
        "/auth/setup",
        json={"email": "second@example.com", "name": "Second", "password": "Secret123"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "the instance owner is already set up"}


@pytest.mark.parametrize(
    ("password", "message"),
    [
        ("short1A", "at least 8 characters"),
        ("nodigitsHere", "at least one number"),
        ("nocapitals1", "capital letter"),
    ],
)
def test_setup_enforces_password_strength(client, password, message):
    response = client.post(
        "/auth/setup", json={"email": "owner@example.com", "name": "Owner", "password": password}
    )

    [error] = response.json()["detail"]
    assert response.status_code == 422
    assert error["loc"] == ["body", "password"]
    assert message in error["msg"]


def test_login_rejects_malformed_email(client):
    response = client.post("/auth/login", json={"email": "not-an-email", "password": "Secret123"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "email"]


def test_logout_ends_the_session(client, owner):
    response = client.post("/auth/logout")

    assert response.status_code == 204
    assert "max-age=0" in response.headers["set-cookie"].lower()
    assert client.get("/auth/me").status_code == 401


def test_login_opens_a_new_session(client, owner):
    client.post("/auth/logout")

    response = client.post(
        "/auth/login", json={"email": "OWNER@example.com", "password": "Secret123"}
    )

    assert response.status_code == 200
    assert response.json()["id"] == owner["id"]
    assert client.get("/auth/me").status_code == 200


def test_login_with_wrong_password_is_unauthorized(client, owner):
    response = client.post(
        "/auth/login", json={"email": "owner@example.com", "password": "Wrong123"}
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "invalid email or password"}
    assert "set-cookie" not in response.headers
