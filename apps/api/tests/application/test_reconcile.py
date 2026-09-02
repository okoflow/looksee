"""Periodic reconciliation of persisted desired state against MediaMTX and inference."""

from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from api.adapters.persistence.models import Camera, Workflow
from api.application import reconcile
from api.application.reconcile import (
    CameraPathPlan,
    plan_camera_paths,
    reconcile_once,
    run_reconcile_loop,
)
from api.domain.enums import CameraSource, CameraStatus
from shared import StartStream, StopStream, WorkflowConfig


class StopLoopError(Exception):
    pass


@pytest.fixture
def seed_camera(fake_session):
    workflow = Workflow(name="Doorway", graph={})
    fake_session.seed(workflow)

    def _seed(revision=1, status=CameraStatus.ACTIVE, start=True, start_command=None):
        camera = Camera(
            workflow_id=workflow.id,
            node_id=f"cam-{len(fake_session.rows[Camera])}",
            name="Front door",
            source_type=CameraSource.RTSP,
            source_url="rtsp://cam.local/stream",
            runtime_revision=revision,
            status=status,
        )
        fake_session.seed(camera)
        if start_command is not None:
            camera.start_command = start_command
        elif start:
            command = StartStream(
                camera_id=camera.id,
                workflow_id=workflow.id,
                revision=revision,
                run_id=uuid4(),
                config=WorkflowConfig(model_id="people"),
            )
            camera.start_command = command.model_dump(mode="json")

        return camera

    return _seed


def test_plan_separates_missing_from_orphaned_paths():
    wanted, orphan_a, orphan_b = uuid4(), uuid4(), uuid4()
    existing = {str(orphan_b), str(orphan_a), "foreign-path"}

    plan = plan_camera_paths([wanted], existing)

    assert plan == CameraPathPlan(
        missing_ids=frozenset({wanted}),
        orphan_ids=tuple(sorted((orphan_a, orphan_b), key=str)),
    )


def test_plan_is_empty_when_paths_already_match():
    camera_id = uuid4()

    plan = plan_camera_paths([camera_id], {str(camera_id)})

    assert plan == CameraPathPlan(missing_ids=frozenset(), orphan_ids=())


async def test_loop_keeps_ticking_after_a_failed_reconcile(monkeypatch, caplog):
    ticks = []
    sleeps = []

    async def failing_once():
        ticks.append(len(ticks))
        if len(ticks) == 1:
            raise RuntimeError("boom")

    async def sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 3:
            raise StopLoopError

    monkeypatch.setattr(reconcile, "asyncio", SimpleNamespace(sleep=sleep))

    with pytest.raises(StopLoopError):
        await run_reconcile_loop(0.5, failing_once)

    assert len(ticks) == 3
    assert sleeps == [0.5, 0.5, 0.5]
    assert "reconcile tick failed" in caplog.text


async def test_camera_without_desired_run_is_told_to_stop(effects, seed_camera):
    camera = seed_camera(revision=4, start=False)

    await reconcile_once()

    assert effects.commands == [StopStream(camera_id=camera.id, revision=4, run_id=None)]


async def test_desired_start_is_republished_every_tick(effects, seed_camera):
    camera = seed_camera()

    await reconcile_once()

    assert effects.commands == [StartStream.model_validate(camera.start_command)]


async def test_corrupt_desired_run_is_cleared_and_marked_errored(
    effects, fake_session, seed_camera
):
    camera = seed_camera(start_command={"type": "start_stream", "revision": -1})

    await reconcile_once()

    assert camera.start_command is None
    assert camera.status is CameraStatus.ERROR
    assert effects.commands == [StopStream(camera_id=camera.id, revision=1, run_id=None)]
    assert fake_session.commits == 1


async def test_revision_drift_is_repaired_from_the_camera_row(effects, seed_camera):
    camera = seed_camera(revision=1)
    camera.runtime_revision = 7

    await reconcile_once()

    assert effects.commands[0].revision == 7
    assert camera.start_command["revision"] == 7


async def test_errored_camera_restart_is_backed_off_between_ticks(effects, seed_camera):
    camera = seed_camera(status=CameraStatus.ERROR)

    await reconcile_once()
    after_first = len(effects.commands)
    await reconcile_once()
    after_second = len(effects.commands)
    effects.runtime_state.clear_worker_retry(camera.id)
    await reconcile_once()

    assert (after_first, after_second, len(effects.commands)) == (1, 1, 2)


async def test_missing_paths_are_provisioned_from_the_camera_row(effects, seed_camera):
    camera = seed_camera()

    await reconcile_once()

    assert effects.upserted_paths == [(camera.id, CameraSource.RTSP, "rtsp://cam.local/stream")]


async def test_existing_paths_are_left_alone(effects, seed_camera):
    camera = seed_camera()
    effects.path_names.add(str(camera.id))

    await reconcile_once()

    assert effects.upserted_paths == []
    assert effects.deleted_paths == []


async def test_orphan_paths_of_unknown_cameras_are_deleted(effects, seed_camera):
    seed_camera()
    orphan = uuid4()
    effects.path_names.update({str(orphan), "not-a-camera"})

    await reconcile_once()

    assert effects.deleted_paths == [orphan]


async def test_path_of_a_camera_created_mid_tick_survives(effects, fake_session, seed_camera):
    late = seed_camera()
    effects.path_names.add(str(late.id))

    await reconcile._delete_orphan_camera_path(late.id)

    assert effects.deleted_paths == []


async def test_mediamtx_outage_is_logged_and_commands_still_flow(
    monkeypatch, effects, seed_camera, caplog
):
    seed_camera()

    async def failing_list():
        raise httpx.ConnectError("refused")

    monkeypatch.setattr(reconcile, "list_path_names", failing_list)

    await reconcile_once()

    assert "mediamtx path listing failed" in caplog.text
    assert len(effects.commands) == 1


async def test_one_failed_publish_does_not_block_the_others(
    monkeypatch, effects, seed_camera, caplog
):
    poisoned = seed_camera()
    healthy = seed_camera()
    published = []

    async def publish(command):
        if command.camera_id == poisoned.id:
            raise RuntimeError("redis hiccup")
        published.append(command.camera_id)

    monkeypatch.setattr(reconcile, "publish_stream_command", publish)

    await reconcile_once()

    assert published == [healthy.id]
    assert f"reconcile failed for camera {poisoned.id}" in caplog.text
