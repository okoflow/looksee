"""HTTP fixtures: the real FastAPI app with persistence and effects swapped for fakes."""

import pytest
from fastapi.testclient import TestClient

from api.adapters.persistence.db import get_session
from api.application.entitlements import COMMUNITY_ENTITLEMENTS, Entitlements
from api.entrypoints.http.dependencies import get_entitlements, get_model_catalog
from api.main import app

OWNER = {"email": "owner@example.com", "name": "Owner", "password": "Secret123"}
ENTERPRISE = Entitlements(
    edition="enterprise",
    features=frozenset({"measurement_filters", "enterprise_integrations"}),
)


@pytest.fixture
def client(fake_session, effects, catalog):
    async def override_session():
        yield fake_session

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_model_catalog] = lambda: catalog
    app.dependency_overrides[get_entitlements] = lambda: COMMUNITY_ENTITLEMENTS

    yield TestClient(app)

    app.dependency_overrides.clear()


@pytest.fixture
def grant_enterprise():
    def _grant():
        app.dependency_overrides[get_entitlements] = lambda: ENTERPRISE

    return _grant


@pytest.fixture
def owner(client):
    response = client.post("/auth/setup", json=OWNER)
    assert response.status_code == 201

    return response.json()
