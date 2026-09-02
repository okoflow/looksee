"""Liveness and schema generation of the composed application."""

from api.config import settings


def test_health_is_public(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_document_is_generated(client):
    schema = client.app.openapi()

    assert schema["info"]["title"] == settings.app_name
    assert {"/health", "/auth/login", "/workflows/{workflow_id}", "/credentials"} <= set(
        schema["paths"]
    )
    assert "WorkflowPatch" in schema["components"]["schemas"]
