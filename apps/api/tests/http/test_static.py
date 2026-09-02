"""Session-gated snapshot file serving."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from starlette.applications import Starlette

from api.adapters.security import issue_session_token
from api.entrypoints.http.dependencies import SESSION_COOKIE
from api.entrypoints.http.static import AuthenticatedStaticFiles


@pytest.fixture
def client(tmp_path):
    (tmp_path / "evidence.jpg").write_bytes(b"jpeg")
    app = Starlette()
    app.mount("/snapshots", AuthenticatedStaticFiles(directory=tmp_path), name="snapshots")

    return TestClient(app)


def test_anonymous_request_is_rejected_before_touching_files(client):
    response = client.get("/snapshots/evidence.jpg")

    assert response.status_code == 401
    assert response.json() == {"detail": "authentication required"}


def test_invalid_cookie_is_rejected(client):
    client.cookies.set(SESSION_COOKIE, "forged")

    assert client.get("/snapshots/evidence.jpg").status_code == 401


def test_valid_session_serves_the_file(client):
    client.cookies.set(SESSION_COOKIE, issue_session_token(uuid4()))

    response = client.get("/snapshots/evidence.jpg")

    assert response.status_code == 200
    assert response.content == b"jpeg"


def test_valid_session_still_gets_not_found_for_missing_files(client):
    client.cookies.set(SESSION_COOKIE, issue_session_token(uuid4()))

    assert client.get("/snapshots/missing.jpg").status_code == 404
