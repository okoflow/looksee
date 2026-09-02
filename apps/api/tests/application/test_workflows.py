"""Workflow create/update/delete use cases with an in-memory session and recorded effects."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from api.adapters.persistence.models import Camera, Credential, Workflow
from api.application import workflows
from api.application.entitlements import COMMUNITY_ENTITLEMENTS, Entitlements
from api.application.errors import ResourceConflictError, ResourceNotFoundError
from api.application.workflows import WorkflowPatch
from api.domain.enums import CameraSource, CameraStatus
from api.domain.errors import GraphErrorCode, WorkflowGraphError
from shared import StartStream, StopStream

ENTERPRISE = Entitlements(edition="enterprise", features=frozenset({"measurement_filters"}))


@pytest.fixture
def create(fake_session, effects, basic_graph):
    async def _create(name="Doorway", graph=basic_graph):
        return await workflows.create_workflow(
            fake_session, name=name, description=None, graph=graph
        )

    return _create


@pytest.fixture
def update(fake_session, catalog):
    async def _update(workflow_id, entitlements=COMMUNITY_ENTITLEMENTS, **fields):
        return await workflows.update_workflow(
            fake_session, workflow_id, WorkflowPatch(**fields), catalog, entitlements
        )

    return _update


async def test_create_persists_graph_and_projects_sources_into_cameras(
    create, fake_session, effects
):
    workflow = await create()

    camera = fake_session.rows[Camera][0]
    assert workflow.enabled is False
    assert [node["id"] for node in workflow.graph["nodes"]] == ["cam", "det", "alert"]
    assert [c.node_id for c in workflow.cameras] == ["cam"]
    assert (camera.name, camera.source_type, camera.source_url) == (
        "Front door",
        CameraSource.RTSP,
        "rtsp://cam.local/stream",
    )
    assert camera.status is CameraStatus.DISABLED
    assert camera.start_command is None


async def test_create_provisions_a_media_path_but_starts_nothing(create, fake_session, effects):
    await create()

    camera = fake_session.rows[Camera][0]
    assert effects.upserted_paths == [(camera.id, CameraSource.RTSP, "rtsp://cam.local/stream")]
    assert effects.commands == []


async def test_create_with_duplicate_name_reports_conflict(create, fake_session):
    await create(name="Doorway")

    with pytest.raises(ResourceConflictError, match="'Doorway' already exists"):
        await create(name="Doorway")

    assert len(fake_session.rows[Workflow]) == 1
    assert fake_session.rollbacks == 1


async def test_create_without_sources_creates_no_cameras(
    create, build_graph, fake_session, effects
):
    graph = build_graph({"alert": {"kind": "log_alert_action"}})

    workflow = await create(graph=graph)

    assert workflow.cameras == []
    assert effects.upserted_paths == []


async def test_get_unknown_workflow_raises_not_found(fake_session):
    with pytest.raises(ResourceNotFoundError, match="workflow not found"):
        await workflows.get_workflow(fake_session, uuid4())


async def test_list_orders_newest_first(create, fake_session):
    first = await create(name="First")
    second = await create(name="Second")
    first.created_at = first.created_at.replace(year=2020)

    listed = await workflows.list_workflows(fake_session)

    assert [w.name for w in listed] == [second.name, first.name]


async def test_enable_validates_then_starts_each_camera(create, update, fake_session, effects):
    workflow = await create()

    enabled = await update(workflow.id, enabled=True)

    camera = fake_session.rows[Camera][0]
    command = StartStream.model_validate(camera.start_command)
    assert enabled.enabled is True
    assert camera.status is CameraStatus.PENDING
    assert camera.runtime_revision == 1
    assert command.revision == 1
    assert command.workflow_id == workflow.id
    assert command.config.model_id == "people"
    assert effects.commands == [command]


async def test_enable_with_invalid_graph_leaves_workflow_disabled(
    create, update, fake_session, effects
):
    workflow = await create()
    workflow.graph["nodes"][1]["data"]["model_id"] = "missing-model"

    with pytest.raises(WorkflowGraphError) as excinfo:
        await update(workflow.id, enabled=True)

    assert excinfo.value.code is GraphErrorCode.MODEL_UNAVAILABLE
    assert fake_session.rows[Workflow][0].enabled is False
    assert effects.commands == []


async def test_disabled_workflow_accepts_any_graph_without_validation(create, update, build_graph):
    workflow = await create()
    broken = build_graph({"det": {"kind": "detect"}})

    updated = await update(workflow.id, graph=broken)

    assert updated.graph["nodes"][0]["data"]["model_id"] is None


async def test_re_enabling_an_unchanged_workflow_does_not_restart(
    create, update, fake_session, effects
):
    workflow = await create()
    await update(workflow.id, enabled=True)
    published_before = list(effects.commands)

    await update(workflow.id, enabled=True)

    camera = fake_session.rows[Camera][0]
    assert camera.runtime_revision == 1
    assert effects.commands == published_before


async def test_disable_stops_the_active_run_and_clears_desired_state(
    create, update, fake_session, effects
):
    workflow = await create()
    await update(workflow.id, enabled=True)
    started = effects.commands[-1]

    await update(workflow.id, enabled=False)

    camera = fake_session.rows[Camera][0]
    stop = effects.commands[-1]
    assert isinstance(stop, StopStream)
    assert stop == StopStream(camera_id=camera.id, revision=2, run_id=started.run_id)
    assert camera.start_command is None
    assert camera.status is CameraStatus.DISABLED


async def test_changing_a_source_url_restarts_that_camera(
    create, update, fake_session, effects, build_graph, basic_nodes
):
    workflow = await create()
    await update(workflow.id, enabled=True)
    first_start = effects.commands[-1]
    basic_nodes["cam"]["url"] = "rtsp://cam.local/other"
    changed = build_graph(basic_nodes, [("cam", "det"), ("det", "alert")])

    await update(workflow.id, graph=changed)

    camera = fake_session.rows[Camera][0]
    second_start = effects.commands[-1]
    assert camera.source_url == "rtsp://cam.local/other"
    assert effects.upserted_paths[-1] == (camera.id, CameraSource.RTSP, "rtsp://cam.local/other")
    assert isinstance(second_start, StartStream)
    assert second_start.revision == first_start.revision + 1
    assert second_start.run_id != first_start.run_id


async def test_changing_only_detect_parameters_restarts_with_new_config(
    create, update, fake_session, effects, build_graph, basic_nodes
):
    workflow = await create()
    await update(workflow.id, enabled=True)
    basic_nodes["det"]["confidence_threshold"] = 0.8
    changed = build_graph(basic_nodes, [("cam", "det"), ("det", "alert")])

    await update(workflow.id, graph=changed)

    restart = effects.commands[-1]
    assert isinstance(restart, StartStream)
    assert restart.config.confidence_threshold == 0.8
    assert len(effects.upserted_paths) == 1


async def test_removing_a_source_deletes_its_camera_and_path(
    create, update, fake_session, effects, build_graph, basic_nodes
):
    workflow = await create()
    await update(workflow.id, enabled=True)
    camera_id = fake_session.rows[Camera][0].id
    started = effects.commands[-1]
    del basic_nodes["cam"]
    without_source = build_graph(basic_nodes, [("det", "alert")])

    await update(workflow.id, graph=without_source, enabled=False)

    assert fake_session.rows[Camera] == []
    assert effects.deleted_paths == [camera_id]
    assert StopStream(camera_id=camera_id, revision=2, run_id=started.run_id) in effects.commands


async def test_delete_stops_cameras_and_removes_paths(create, update, fake_session, effects):
    workflow = await create()
    await update(workflow.id, enabled=True)
    camera_id = fake_session.rows[Camera][0].id
    started = effects.commands[-1]

    await workflows.delete_workflow(fake_session, workflow.id)

    assert fake_session.rows[Workflow] == []
    assert fake_session.rows[Camera] == []
    assert effects.deleted_paths == [camera_id]
    assert effects.commands[-1] == StopStream(
        camera_id=camera_id, revision=2, run_id=started.run_id
    )


async def test_delete_unknown_workflow_raises_not_found(fake_session):
    with pytest.raises(ResourceNotFoundError):
        await workflows.delete_workflow(fake_session, uuid4())


async def test_rename_to_an_existing_name_reports_conflict(create, update):
    await create(name="Taken")
    other = await create(name="Other")

    with pytest.raises(ResourceConflictError, match="'Taken' already exists"):
        await update(other.id, name="Taken")


async def test_patch_applies_only_sent_fields(create, update):
    workflow = await create()

    renamed = await update(workflow.id, name="Renamed", description="")

    assert renamed.name == "Renamed"
    assert renamed.description == ""
    assert renamed.enabled is False


def test_patch_rejects_unknown_fields():
    with pytest.raises(ValueError, match="extra"):
        WorkflowPatch(colour="red")


async def test_enterprise_node_requires_entitlement(create, update, build_graph, basic_nodes):
    basic_nodes["line"] = {
        "kind": "line_crossing_filter",
        "line": [[0.1, 0.5], [0.9, 0.5]],
    }
    graph = build_graph(basic_nodes, [("cam", "det"), ("det", "line"), ("line", "alert")])
    workflow = await create(graph=graph)

    with pytest.raises(WorkflowGraphError) as excinfo:
        await update(workflow.id, enabled=True)
    licensed = await update(workflow.id, enabled=True, entitlements=ENTERPRISE)

    assert excinfo.value.code is GraphErrorCode.FEATURE_NOT_LICENSED
    assert excinfo.value.node_id == "line"
    assert licensed.enabled is True


async def test_enable_checks_credentials_exist_for_actions(
    create, update, fake_session, build_graph, basic_nodes
):
    credential = Credential(
        name="bot", type="telegram_bot", summary="Telegram bot", encrypted_payload="x"
    )
    fake_session.seed(credential)
    basic_nodes["tg"] = {
        "kind": "telegram_action",
        "credential_id": str(credential.id),
        "chat_id": "42",
    }
    graph = build_graph(basic_nodes, [("cam", "det"), ("det", "tg")])
    workflow = await create(graph=graph)

    enabled = await update(workflow.id, enabled=True)

    assert enabled.enabled is True


async def test_unrelated_integrity_errors_propagate(create, fake_session, monkeypatch):
    async def failing_commit():
        raise IntegrityError("INSERT", {}, Exception("check constraint"))

    monkeypatch.setattr(fake_session, "commit", failing_commit)

    with pytest.raises(IntegrityError):
        await create()
