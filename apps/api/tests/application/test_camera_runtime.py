"""Camera desired-state projection: run fencing, revisions, and post-commit effects."""

from uuid import uuid4

import pytest

from api.adapters.persistence.models import Camera, Workflow
from api.application import camera_runtime
from api.application.camera_policy import matches_desired_run
from api.application.camera_runtime import (
    CameraRuntimePlan,
    apply_camera_runtime_plan,
    inference_config,
    parse_start_command,
    start_is_current,
    start_workflow_cameras,
    stop_workflow_cameras,
    sync_workflow_cameras,
    teardown_workflow_cameras,
)
from api.domain.enums import CameraSource, CameraStatus
from api.domain.graph import WorkflowGraphIndex
from shared import StartStream, StopStream, WorkflowConfig


@pytest.fixture
def desired():
    return StartStream(
        camera_id=uuid4(),
        workflow_id=uuid4(),
        revision=3,
        run_id=uuid4(),
        config=WorkflowConfig(model_id="people"),
    )


@pytest.fixture
def workflow(fake_session):
    row = Workflow(name="Doorway", graph={})
    fake_session.seed(row)

    return row


def test_report_matches_when_every_identity_field_agrees(desired, make_frame):
    frame = make_frame(
        workflow_id=desired.workflow_id,
        revision=desired.revision,
        run_id=desired.run_id,
        model_id="people",
    )

    assert matches_desired_run(frame, desired) is True


@pytest.mark.parametrize(
    "mismatch",
    [
        {"workflow_id": uuid4()},
        {"revision": 2},
        {"run_id": uuid4()},
        {"model_id": "other"},
    ],
)
def test_report_with_any_identity_mismatch_is_rejected(desired, make_frame, mismatch):
    fields = {
        "workflow_id": desired.workflow_id,
        "revision": desired.revision,
        "run_id": desired.run_id,
        "model_id": "people",
    }
    fields.update(mismatch)

    assert matches_desired_run(make_frame(**fields), desired) is False


def test_start_is_current_only_for_same_revision_workflow_and_config(desired):
    current = start_is_current(
        desired,
        workflow_id=desired.workflow_id,
        runtime_revision=3,
        config=desired.config,
        force_restart=False,
    )

    assert current is True


@pytest.mark.parametrize(
    "overrides",
    [
        {"current": None},
        {"force_restart": True},
        {"runtime_revision": 4},
        {"workflow_id": uuid4()},
        {"config": WorkflowConfig(model_id="people", inference_fps=5)},
    ],
)
def test_start_is_stale_when_anything_differs(desired, overrides):
    arguments = {
        "current": desired,
        "workflow_id": desired.workflow_id,
        "runtime_revision": 3,
        "config": desired.config,
        "force_restart": False,
    }
    arguments.update(overrides)

    assert start_is_current(**arguments) is False


def test_parse_start_command_accepts_a_persisted_document(desired):
    assert parse_start_command(desired.camera_id, desired.model_dump(mode="json")) == desired


def test_parse_start_command_treats_missing_as_none():
    assert parse_start_command(uuid4(), None) is None


def test_parse_start_command_warns_on_invalid_document(caplog):
    camera_id = uuid4()

    parsed = parse_start_command(camera_id, {"type": "start_stream", "revision": -1})

    assert parsed is None
    assert f"invalid persisted start command camera={camera_id}" in caplog.text


def test_inference_config_comes_from_the_selected_detect_node(build_graph, basic_nodes):
    basic_nodes["det"].update({"confidence_threshold": 0.7, "inference_fps": 4})
    index = WorkflowGraphIndex.build(build_graph(basic_nodes, [("cam", "det")]))

    config = inference_config(index, "cam")

    assert config == WorkflowConfig(model_id="people", confidence_threshold=0.7, inference_fps=4)


async def test_sync_creates_cameras_for_new_sources(fake_session, workflow, basic_graph):
    plan = await sync_workflow_cameras(
        fake_session, workflow, WorkflowGraphIndex.build(basic_graph)
    )

    camera = fake_session.rows[Camera][0]
    assert camera.workflow_id == workflow.id
    assert camera.node_id == "cam"
    assert plan.upsert_path_ids == {camera.id}
    assert plan.restart_camera_ids == set()
    assert plan.commands == []


@pytest.mark.parametrize(
    ("source", "expected_url"),
    [
        ({"kind": "camera_source", "source_type": "webrtc", "url": "ignored"}, None),
        ({"kind": "camera_source", "source_type": "rtsp", "url": ""}, None),
        ({"kind": "camera_source", "source_type": "file", "url": "clip.mp4"}, "clip.mp4"),
    ],
)
async def test_sync_persists_only_meaningful_source_urls(
    fake_session, workflow, build_graph, source, expected_url
):
    index = WorkflowGraphIndex.build(build_graph({"cam": source}))

    await sync_workflow_cameras(fake_session, workflow, index)

    assert fake_session.rows[Camera][0].source_url == expected_url


async def test_sync_renames_without_restart_but_restarts_on_source_change(
    fake_session, workflow, build_graph, basic_nodes
):
    await sync_workflow_cameras(
        fake_session, workflow, WorkflowGraphIndex.build(build_graph(basic_nodes))
    )
    camera = fake_session.rows[Camera][0]
    basic_nodes["cam"]["name"] = "Back door"
    renamed = await sync_workflow_cameras(
        fake_session, workflow, WorkflowGraphIndex.build(build_graph(basic_nodes))
    )
    basic_nodes["cam"].update({"source_type": "rtmp", "url": "rtmp://cam/live"})

    changed = await sync_workflow_cameras(
        fake_session, workflow, WorkflowGraphIndex.build(build_graph(basic_nodes))
    )

    assert camera.name == "Back door"
    assert renamed.restart_camera_ids == set()
    assert changed.restart_camera_ids == {camera.id}
    assert changed.upsert_path_ids == {camera.id}
    assert camera.source_type is CameraSource.RTMP


async def test_start_assigns_a_fresh_run_and_bumps_the_revision(
    fake_session, workflow, basic_graph
):
    index = WorkflowGraphIndex.build(basic_graph)
    await sync_workflow_cameras(fake_session, workflow, index)

    plan = await start_workflow_cameras(fake_session, workflow, index)

    camera = fake_session.rows[Camera][0]
    command = plan.commands[0]
    assert isinstance(command, StartStream)
    assert camera.runtime_revision == 1
    assert command.revision == 1
    assert command.camera_id == camera.id
    assert camera.start_command == command.model_dump(mode="json")
    assert camera.status is CameraStatus.PENDING


async def test_start_is_idempotent_until_config_or_restart_changes(
    fake_session, workflow, basic_graph
):
    index = WorkflowGraphIndex.build(basic_graph)
    await sync_workflow_cameras(fake_session, workflow, index)
    first = await start_workflow_cameras(fake_session, workflow, index)
    camera = fake_session.rows[Camera][0]

    unchanged = await start_workflow_cameras(fake_session, workflow, index)
    forced = await start_workflow_cameras(
        fake_session, workflow, index, CameraRuntimePlan(restart_camera_ids={camera.id})
    )

    assert unchanged.commands == []
    assert forced.commands[0].revision == first.commands[0].revision + 1
    assert forced.commands[0].run_id != first.commands[0].run_id


async def test_stop_targets_the_current_run_and_disables_the_camera(
    fake_session, workflow, basic_graph
):
    index = WorkflowGraphIndex.build(basic_graph)
    await sync_workflow_cameras(fake_session, workflow, index)
    started = (await start_workflow_cameras(fake_session, workflow, index)).commands[0]

    plan = await stop_workflow_cameras(fake_session, workflow)

    camera = fake_session.rows[Camera][0]
    assert plan.commands == [StopStream(camera_id=camera.id, revision=2, run_id=started.run_id)]
    assert camera.start_command is None
    assert camera.status is CameraStatus.DISABLED


async def test_stop_of_a_never_started_camera_cancels_any_run(fake_session, workflow, basic_graph):
    await sync_workflow_cameras(fake_session, workflow, WorkflowGraphIndex.build(basic_graph))

    plan = await stop_workflow_cameras(fake_session, workflow)

    camera = fake_session.rows[Camera][0]
    assert plan.commands == [StopStream(camera_id=camera.id, revision=1, run_id=None)]


async def test_teardown_plans_stops_and_path_deletes_but_keeps_rows(
    fake_session, workflow, basic_graph
):
    await sync_workflow_cameras(fake_session, workflow, WorkflowGraphIndex.build(basic_graph))
    camera = fake_session.rows[Camera][0]

    plan = await teardown_workflow_cameras(fake_session, workflow)

    assert plan.delete_path_ids == [camera.id]
    assert [type(command) for command in plan.commands] == [StopStream]
    assert fake_session.rows[Camera] == [camera]


async def test_apply_runs_upserts_then_commands_then_deletes(
    monkeypatch, fake_session, workflow, desired
):
    camera = Camera(
        workflow_id=workflow.id,
        node_id="cam",
        name="c",
        source_type=CameraSource.RTSP,
        source_url="rtsp://a",
    )
    fake_session.seed(camera)
    order = []

    async def upsert(camera_id, source_type, source_url):
        order.append(("upsert", camera_id))

    async def publish(command):
        order.append(("publish", command.camera_id))

    async def delete(camera_id):
        order.append(("delete", camera_id))

    monkeypatch.setattr(camera_runtime, "session_factory", lambda: fake_session)
    monkeypatch.setattr(camera_runtime, "upsert_camera_path", upsert)
    monkeypatch.setattr(camera_runtime, "publish_stream_command", publish)
    monkeypatch.setattr(camera_runtime, "delete_camera_path", delete)
    other_id = uuid4()

    await apply_camera_runtime_plan(
        CameraRuntimePlan(
            upsert_path_ids={camera.id}, commands=[desired], delete_path_ids=[other_id]
        )
    )

    assert order == [("upsert", camera.id), ("publish", desired.camera_id), ("delete", other_id)]


async def test_apply_upserts_the_committed_source_of_each_camera(effects, fake_session, workflow):
    camera = Camera(
        workflow_id=workflow.id,
        node_id="cam",
        name="c",
        source_type=CameraSource.WHEP,
        source_url="https://cam/whep",
    )
    fake_session.seed(camera)

    await apply_camera_runtime_plan(CameraRuntimePlan(upsert_path_ids={camera.id}))

    assert effects.upserted_paths == [(camera.id, CameraSource.WHEP, "https://cam/whep")]


async def test_apply_caches_file_sources_before_upserting(effects, fake_session, workflow):
    camera = Camera(
        workflow_id=workflow.id,
        node_id="cam",
        name="c",
        source_type=CameraSource.FILE,
        source_url="clips/a.mp4",
    )
    fake_session.seed(camera)
    effects.cached_names["clips/a.mp4"] = "0123abcd-4567ef01.mp4"

    await apply_camera_runtime_plan(CameraRuntimePlan(upsert_path_ids={camera.id}))

    assert effects.upserted_paths == [(camera.id, CameraSource.FILE, "0123abcd-4567ef01.mp4")]


async def test_apply_deletes_the_path_of_a_camera_that_vanished(effects):
    gone = uuid4()

    await apply_camera_runtime_plan(CameraRuntimePlan(upsert_path_ids={gone}))

    assert effects.upserted_paths == []
    assert effects.deleted_paths == [gone]


async def test_apply_logs_and_continues_when_provisioning_fails(
    effects, fake_session, workflow, caplog
):
    camera = Camera(
        workflow_id=workflow.id,
        node_id="cam",
        name="c",
        source_type=CameraSource.RTSP,
        source_url="rtsp://a",
    )
    fake_session.seed(camera)
    effects.upsert_error = RuntimeError("mediamtx down")

    await apply_camera_runtime_plan(CameraRuntimePlan(upsert_path_ids={camera.id}))

    assert f"mediamtx provisioning failed camera={camera.id}" in caplog.text


async def test_apply_logs_publish_failures_and_still_deletes_paths(effects, desired, caplog):
    effects.publish_error = RuntimeError("redis down")
    orphan = uuid4()

    await apply_camera_runtime_plan(CameraRuntimePlan(commands=[desired], delete_path_ids=[orphan]))

    assert (
        f"stream command publish failed camera={desired.camera_id} type=start_stream" in caplog.text
    )
    assert effects.deleted_paths == [orphan]
