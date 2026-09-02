"""Every non-auth router refuses requests without a valid session."""

from uuid import uuid4

import pytest

from api.adapters.security import issue_session_token
from api.entrypoints.http.dependencies import SESSION_COOKIE

PROTECTED = [
    ("GET", "/workflows"),
    ("POST", "/workflows"),
    ("GET", f"/workflows/{uuid4()}"),
    ("PATCH", f"/workflows/{uuid4()}"),
    ("DELETE", f"/workflows/{uuid4()}"),
    ("GET", "/alerts"),
    ("DELETE", "/alerts"),
    ("GET", "/credentials"),
    ("POST", "/credentials"),
    ("GET", "/entitlements"),
    ("GET", "/models"),
    ("GET", "/assets"),
    ("GET", "/auth/me"),
]


@pytest.mark.parametrize(("method", "path"), PROTECTED)
def test_anonymous_requests_are_rejected(client, method, path):
    response = client.request(method, path, json={})

    assert response.status_code == 401
    assert response.json() == {"detail": "authentication required"}


def test_tampered_cookie_is_rejected(client, owner):
    client.cookies.set(SESSION_COOKIE, "not-a-token")

    assert client.get("/auth/me").status_code == 401


def test_valid_token_for_a_deleted_user_is_rejected(client):
    client.cookies.set(SESSION_COOKIE, issue_session_token(uuid4()))

    assert client.get("/auth/me").status_code == 401


def test_session_cookie_grants_access(client, owner):
    assert client.get("/models").status_code == 200
