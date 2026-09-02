"""Worker lifecycle events projected onto camera status with run fencing."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from api.adapters.persistence.models import Camera, Workflow
from api.application.worker_status import (
    WorkerStatusDecision,
    WorkerTarget,
    apply_worker_event,
    decide_worker_event,
)
from api.domain.enums import CameraSource, CameraStatus
from shared import (
    StartStream,
    StopStream,
    WorkerErrored,
    WorkerStarted,
    WorkerStopped,
    WorkflowConfig,
)

TS = datetime(2026, 3, 4, 12, 0, tzinfo=UTC)


@pytest.fixture
def desired():
    return StartStream(
        camera_id=uuid4(),
        workflow_id=uuid4(),
        revision=2,
        run_id=uuid4(),
        config=WorkflowConfig(model_id="people"),
    )


def event_for(desired, event_type=WorkerStarted, **overrides):
    fields = {
        "camera_id": desired.camera_id,
        "workflow_id": desired.workflow_id,
        "revision": desired.revision,
        "run_id": desired.run_id,
        "model_id": desired.config.model_id,
        "timestamp": TS,
    }
    fields.update(overrides)

    return event_type(**fields)


def test_started_worker_of_unknown_camera_is_cancelled(desired):
    event = event_for(desired)

    decision = decide_worker_event(None, event)

    assert decision == WorkerStatusDecision(
        stop_command=StopStream(camera_id=event.camera_id, revision=2, run_id=event.run_id)
    )


@pytest.mark.parametrize("event_type", [WorkerStopped, WorkerErrored])
def test_finished_worker_of_unknown_camera_needs_no_cancellation(desired, event_type):
    decision = decide_worker_event(None, event_for(desired, event_type))

    assert decision == WorkerStatusDecision()


def test_clean_stop_at_current_revision_disables_a_camera_without_desired_run(desired):
    target = WorkerTarget(runtime_revision=2, desired_start=None)

    decision = decide_worker_event(target, event_for(desired, WorkerStopped))

    assert decision == WorkerStatusDecision(status=CameraStatus.DISABLED)


def test_started_worker_on_a_disabled_camera_is_cancelled(desired):
    target = WorkerTarget(runtime_revision=2, desired_start=None)

    decision = decide_worker_event(target, event_for(desired))

    assert decision.status is None
    assert decision.stop_command is not None


def test_stale_stop_on_a_disabled_camera_changes_nothing(desired):
    target = WorkerTarget(runtime_revision=2, desired_start=None)

    decision = decide_worker_event(target, event_for(desired, WorkerStopped, revision=1))

    assert decision == WorkerStatusDecision()


def test_event_from_a_superseded_run_is_ignored(desired):
    target = WorkerTarget(runtime_revision=2, desired_start=desired)

    decision = decide_worker_event(target, event_for(desired, run_id=uuid4()))

    assert decision == WorkerStatusDecision()


@pytest.mark.parametrize(
    ("event_type", "status"),
    [
        (WorkerStarted, CameraStatus.ACTIVE),
        (WorkerStopped, CameraStatus.DISABLED),
        (WorkerErrored, CameraStatus.ERROR),
    ],
)
def test_matching_events_map_onto_camera_status(desired, event_type, status):
    target = WorkerTarget(runtime_revision=2, desired_start=desired)

    decision = decide_worker_event(target, event_for(desired, event_type))

    assert decision.status is status
    assert decision.stop_command is None


def test_error_reason_is_carried_through(desired):
    target = WorkerTarget(runtime_revision=2, desired_start=desired)

    decision = decide_worker_event(target, event_for(desired, WorkerErrored, reason="rtsp timeout"))

    assert decision.reason == "rtsp timeout"


class TestApplyWorkerEvent:
    @pytest.fixture
    def camera(self, fake_session, desired):
        workflow = Workflow(name="Doorway", graph={})
        fake_session.seed(workflow)
        row = Camera(
            id=desired.camera_id,
            workflow_id=workflow.id,
            node_id="cam",
            name="Front door",
            source_type=CameraSource.RTSP,
            source_url="rtsp://cam.local/stream",
            runtime_revision=desired.revision,
            status=CameraStatus.PENDING,
        )
        fake_session.seed(row)
        row.start_command = desired.model_copy(update={"workflow_id": workflow.id}).model_dump(
            mode="json"
        )

        return row

    async def test_started_event_activates_camera_and_broadcasts(
        self, effects, fake_session, camera, desired
    ):
        event = event_for(desired, workflow_id=camera.workflow_id)

        await apply_worker_event(fake_session, event)

        assert camera.status is CameraStatus.ACTIVE
        assert fake_session.commits == 1
        assert effects.realtime == [
            (
                camera.id,
                {"type": "worker", "status": "active", "ts": TS.isoformat(), "reason": None},
            )
        ]

    async def test_errored_event_records_reason_and_warns(
        self, effects, fake_session, camera, desired, caplog
    ):
        event = event_for(
            desired, WorkerErrored, workflow_id=camera.workflow_id, reason="decode failed"
        )

        await apply_worker_event(fake_session, event)

        assert camera.status is CameraStatus.ERROR
        assert effects.realtime[0][1]["reason"] == "decode failed"
        assert f"worker errored camera={camera.id} reason=decode failed" in caplog.text

    async def test_unchanged_status_rolls_back_but_still_broadcasts(
        self, effects, fake_session, camera, desired
    ):
        camera.status = CameraStatus.ACTIVE

        await apply_worker_event(fake_session, event_for(desired, workflow_id=camera.workflow_id))

        assert fake_session.commits == 0
        assert fake_session.rollbacks == 1
        assert effects.realtime_types() == ["worker"]

    async def test_superseded_run_changes_nothing(self, effects, fake_session, camera, desired):
        await apply_worker_event(fake_session, event_for(desired, run_id=uuid4()))

        assert camera.status is CameraStatus.PENDING
        assert effects.realtime == []
        assert effects.commands == []

    async def test_orphan_worker_is_stopped_and_logged(
        self, effects, fake_session, desired, caplog
    ):
        caplog.set_level("INFO", logger="api.application.worker_status")
        event = event_for(desired)

        await apply_worker_event(fake_session, event)

        assert effects.commands == [
            StopStream(camera_id=event.camera_id, revision=2, run_id=event.run_id)
        ]
        assert f"stopping orphan worker camera={event.camera_id}" in caplog.text
        assert effects.realtime == []

    async def test_successful_start_clears_pending_retry_backoff(
        self, effects, fake_session, camera, desired
    ):
        effects.runtime_state.note_worker_retry(camera.id, 2, TS, base_seconds=30, cap_seconds=300)

        await apply_worker_event(fake_session, event_for(desired, workflow_id=camera.workflow_id))

        assert effects.runtime_state.worker_retry_ready(camera.id, 2, TS) is True

    async def test_corrupt_desired_run_is_left_for_reconcile(
        self, effects, fake_session, camera, desired
    ):
        camera.start_command = {"type": "start_stream"}

        await apply_worker_event(fake_session, event_for(desired))

        assert camera.status is CameraStatus.PENDING
        assert effects.realtime == []
        assert effects.commands == []
