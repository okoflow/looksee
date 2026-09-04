"""Application failures map onto stable HTTP status codes and bodies."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.application.errors import (
    InvalidCredentialsError,
    ResourceConflictError,
    ResourceNotFoundError,
)
from api.domain.errors import GraphErrorCode, WorkflowGraphError
from api.entrypoints.http.errors import register_exception_handlers


def build_app():
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/not-found")
    def not_found():
        raise ResourceNotFoundError("thing not found")

    @app.get("/conflict")
    def conflict():
        raise ResourceConflictError("thing exists")

    @app.get("/unauthorized")
    def unauthorized():
        raise InvalidCredentialsError("bad login")

    @app.get("/cycle")
    def cycle():
        raise WorkflowGraphError(GraphErrorCode.GRAPH_CYCLE, node_id="n1")

    @app.get("/unlicensed")
    def unlicensed():
        raise WorkflowGraphError(GraphErrorCode.FEATURE_NOT_LICENSED, node_id="n2", feature="f")

    @app.get("/no-source")
    def no_source():
        raise WorkflowGraphError(GraphErrorCode.NO_CAMERA_SOURCE)

    return app


@pytest.fixture
def client():
    return TestClient(build_app())


@pytest.mark.parametrize(
    ("path", "status_code", "detail"),
    [
        ("/not-found", 404, "thing not found"),
        ("/conflict", 409, "thing exists"),
        ("/unauthorized", 401, "bad login"),
    ],
)
def test_application_errors_become_detail_bodies(client, path, status_code, detail):
    response = client.get(path)

    assert response.status_code == status_code
    assert response.json() == {"detail": detail}


@pytest.mark.filterwarnings(
    "ignore:'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated:starlette.exceptions.StarletteDeprecationWarning"
)
def test_graph_errors_carry_code_and_node(client):
    response = client.get("/cycle")

    assert response.status_code == 422
    assert response.json() == {
        "detail": "workflow contains a cycle through node 'n1'",
        "code": "graph_cycle",
        "node_id": "n1",
    }


@pytest.mark.filterwarnings(
    "ignore:'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated:starlette.exceptions.StarletteDeprecationWarning"
)
def test_unlicensed_feature_is_payment_required(client):
    response = client.get("/unlicensed")

    assert response.status_code == 402
    assert response.json()["code"] == "feature_not_licensed"
    assert response.json()["node_id"] == "n2"


@pytest.mark.filterwarnings(
    "ignore:'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated:starlette.exceptions.StarletteDeprecationWarning"
)
def test_graph_error_without_node_reports_null_node(client):
    response = client.get("/no-source")

    assert response.status_code == 422
    assert response.json()["node_id"] is None
    assert response.json()["code"] == "no_camera_source"


def test_graph_error_responses_emit_no_deprecation_warning(client):
    response = client.get("/cycle")

    assert response.status_code == 422
