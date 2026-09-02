"""Workflow CRUD over HTTP, including graph error translation."""

from uuid import uuid4

import pytest

from api.domain.enums import CameraStatus


@pytest.fixture
def create(client, owner, basic_graph):
    def _create(name="Doorway", graph=None):
        document = (graph if graph is not None else basic_graph).model_dump(mode="json")
        response = client.post("/workflows", json={"name": name, "graph": document})
        assert response.status_code == 201, response.text

        return response.json()

    return _create


def test_create_returns_the_persisted_workflow_with_its_cameras(create):
    body = create()

    assert body["name"] == "Doorway"
    assert body["enabled"] is False
    assert [node["id"] for node in body["graph"]["nodes"]] == ["cam", "det", "alert"]
    assert [(c["node_id"], c["name"], c["source_type"], c["status"]) for c in body["cameras"]] == [
        ("cam", "Front door", "rtsp", "disabled")
    ]


def test_create_rejects_unknown_fields(client, owner):
    response = client.post("/workflows", json={"name": "x", "colour": "red"})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "colour"]


def test_create_rejects_an_unknown_node_kind(client, owner):
    graph = {"nodes": [{"id": "n", "position": {"x": 0, "y": 0}, "data": {"kind": "teleport"}}]}

    response = client.post("/workflows", json={"name": "x", "graph": graph})

    assert response.status_code == 422


def test_duplicate_name_is_a_conflict(create, client):
    create(name="Doorway")

    response = client.post("/workflows", json={"name": "Doorway"})

    assert response.status_code == 409
    assert response.json() == {"detail": "Workflow named 'Doorway' already exists"}


def test_list_and_get_round_trip(create, client):
    created = create()

    listed = client.get("/workflows").json()
    fetched = client.get(f"/workflows/{created['id']}")

    assert [w["id"] for w in listed] == [created["id"]]
    assert fetched.status_code == 200
    assert fetched.json() == created


def test_unknown_workflow_is_not_found(client, owner):
    response = client.get(f"/workflows/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "workflow not found"}


def test_malformed_workflow_id_is_a_validation_error(client, owner):
    assert client.get("/workflows/not-a-uuid").status_code == 422


def test_enable_starts_the_cameras(create, client, effects):
    created = create()

    response = client.patch(f"/workflows/{created['id']}", json={"enabled": True})

    body = response.json()
    assert response.status_code == 200
    assert body["enabled"] is True
    assert body["cameras"][0]["status"] == CameraStatus.PENDING
    assert [command.type for command in effects.commands] == ["start_stream"]


@pytest.mark.filterwarnings(
    "ignore:'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated:starlette.exceptions.StarletteDeprecationWarning"
)
def test_enable_with_an_unrunnable_graph_maps_to_422_with_graph_context(
    create, client, basic_graph
):
    created = create()
    document = basic_graph.model_dump(mode="json")
    document["nodes"][1]["data"]["model_id"] = "ghost"

    response = client.patch(
        f"/workflows/{created['id']}", json={"enabled": True, "graph": document}
    )

    assert response.status_code == 422
    assert response.json() == {
        "detail": "detect node 'det' selects unavailable model 'ghost'",
        "code": "model_unavailable",
        "node_id": "det",
    }


@pytest.mark.filterwarnings(
    "ignore:'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated:starlette.exceptions.StarletteDeprecationWarning"
)
def test_unlicensed_node_maps_to_402_until_entitled(
    create, client, build_graph, basic_nodes, grant_enterprise
):
    basic_nodes["line"] = {"kind": "line_crossing_filter", "line": [[0.1, 0.5], [0.9, 0.5]]}
    graph = build_graph(basic_nodes, [("cam", "det"), ("det", "line"), ("line", "alert")])
    created = create(graph=graph)

    refused = client.patch(f"/workflows/{created['id']}", json={"enabled": True})
    grant_enterprise()
    allowed = client.patch(f"/workflows/{created['id']}", json={"enabled": True})

    assert refused.status_code == 402
    assert refused.json()["code"] == "feature_not_licensed"
    assert refused.json()["node_id"] == "line"
    assert allowed.status_code == 200


def test_patch_rejects_unknown_fields(create, client):
    created = create()

    response = client.patch(f"/workflows/{created['id']}", json={"archived": True})

    assert response.status_code == 422


def test_delete_removes_the_workflow(create, client, effects):
    created = create()

    response = client.delete(f"/workflows/{created['id']}")

    assert response.status_code == 204
    assert client.get(f"/workflows/{created['id']}").status_code == 404
    assert len(effects.deleted_paths) == 1
