"""Accepted frames: realtime fan-out, cooldown, and run fencing against persisted state."""

from dataclasses import replace
from datetime import timedelta
from uuid import uuid4

import pytest

from api.adapters.persistence.models import Camera, Workflow
from api.application.errors import RetryableFrameError
from api.application.execution import ExecutionIdentity
from api.application.frame_processing import handle_detection_frame, process_frame
from api.domain.enums import CameraSource, CameraStatus
from api.domain.graph import WorkflowGraphIndex
from shared import StartStream, StopStream, WorkflowConfig


async def run(frame, index, identity, people_model, dependencies):
    await process_frame(frame, people_model, index, "cam", identity, dependencies)


async def test_frame_publishes_detections_then_event_then_runs_actions(
    effects, basic_graph, make_frame, identity, people_model
):
    frame = make_frame()

    await run(frame, WorkflowGraphIndex.build(basic_graph), identity, people_model, effects.frames)

    assert effects.realtime_types() == ["detections", "event"]
    assert effects.realtime[0][0] == frame.camera_id
    assert effects.realtime[1][1]["kind"] == "PERSON_DETECTED"
    assert effects.realtime[1][1]["ts"] == frame.timestamp.isoformat()
    assert [action.kind for _, _, action, _ in effects.actions] == ["log_alert_action"]


async def test_frame_without_events_only_publishes_detections(
    effects, basic_graph, make_frame, make_detection, identity, people_model
):
    frame = make_frame(detections=(make_detection(label="background", class_id=2),))

    await run(frame, WorkflowGraphIndex.build(basic_graph), identity, people_model, effects.frames)

    assert effects.realtime_types() == ["detections"]
    assert effects.actions == []


async def test_cooldown_limits_realtime_without_skipping_workflow_execution(
    effects, basic_graph, make_frame, identity, people_model
):
    dependencies = replace(effects.frames, event_cooldown_seconds=2.0)
    index = WorkflowGraphIndex.build(basic_graph)
    camera_id = uuid4()

    await run(make_frame(camera_id=camera_id), index, identity, people_model, dependencies)
    await run(make_frame(camera_id=camera_id), index, identity, people_model, dependencies)

    assert effects.realtime_types() == ["detections", "event", "detections"]
    assert len(effects.actions) == 2


async def test_cooldown_is_scoped_per_run(effects, basic_graph, make_frame, identity, people_model):
    dependencies = replace(effects.frames, event_cooldown_seconds=2.0)
    index = WorkflowGraphIndex.build(basic_graph)
    camera_id = uuid4()
    other_run = replace(identity, run_id=uuid4())

    await run(make_frame(camera_id=camera_id), index, identity, people_model, dependencies)
    await run(make_frame(camera_id=camera_id), index, other_run, people_model, dependencies)

    assert len(effects.actions) == 2


async def test_zero_cooldown_processes_every_frame(
    effects, basic_graph, make_frame, identity, people_model
):
    index = WorkflowGraphIndex.build(basic_graph)
    camera_id = uuid4()

    await run(make_frame(camera_id=camera_id), index, identity, people_model, effects.frames)
    await run(make_frame(camera_id=camera_id), index, identity, people_model, effects.frames)

    assert len(effects.actions) == 2


async def test_line_crossing_is_observed_inside_realtime_cooldown(
    effects,
    basic_nodes,
    build_graph,
    make_frame,
    make_detection,
    identity,
    people_model,
):
    nodes = {
        **basic_nodes,
        "line": {"kind": "line_crossing_filter", "line": [(0.5, 0), (0.5, 1)]},
    }
    index = WorkflowGraphIndex.build(
        build_graph(
            nodes,
            [("cam", "det"), ("det", "line"), ("line", "alert")],
        )
    )
    dependencies = replace(effects.frames, event_cooldown_seconds=2)
    before = make_frame(
        detections=(make_detection(tracker_id=7, bounding_box=(100, 100, 300, 400)),)
    )
    after = before.model_copy(
        update={
            "timestamp": before.timestamp + timedelta(milliseconds=100),
            "detections": (make_detection(tracker_id=7, bounding_box=(900, 100, 1100, 400)),),
        }
    )

    await run(before, index, identity, people_model, dependencies)
    await run(after, index, identity, people_model, dependencies)

    assert len(effects.actions) == 1
    assert effects.actions[0][1].ts == after.timestamp
    assert effects.realtime_types() == ["detections", "event", "detections"]


async def test_failed_queue_write_does_not_consume_debounce(
    effects,
    basic_nodes,
    build_graph,
    make_frame,
    identity,
    people_model,
):
    nodes = {**basic_nodes, "debounce": {"kind": "debounce_filter", "seconds": 30}}
    index = WorkflowGraphIndex.build(
        build_graph(
            nodes,
            [("cam", "det"), ("det", "debounce"), ("debounce", "alert")],
        )
    )
    attempts = []

    async def persist(*args):
        attempts.append(args)
        if len(attempts) == 1:
            raise RetryableFrameError("database unavailable")

    dependencies = replace(effects.frames, run_action=persist)
    frame = make_frame()

    with pytest.raises(RetryableFrameError):
        await run(frame, index, identity, people_model, dependencies)

    await run(frame, index, identity, people_model, dependencies)

    assert len(attempts) == 2


class TestHandleDetectionFrame:
    def seed(self, fake_session, basic_graph, enabled=True, revision=1):
        workflow = Workflow(
            name="Doorway", enabled=enabled, graph=basic_graph.model_dump(mode="json")
        )
        fake_session.seed(workflow)
        camera = Camera(
            workflow_id=workflow.id,
            node_id="cam",
            name="Front door",
            source_type=CameraSource.RTSP,
            source_url="rtsp://cam.local/stream",
            runtime_revision=revision,
            status=CameraStatus.ACTIVE,
        )
        fake_session.seed(camera)
        start = StartStream(
            camera_id=camera.id,
            workflow_id=workflow.id,
            revision=revision,
            run_id=uuid4(),
            config=WorkflowConfig(model_id="people"),
        )
        camera.start_command = start.model_dump(mode="json")

        return (workflow, camera, start)

    def matching_frame(self, make_frame, camera, start, **overrides):
        fields = {
            "camera_id": camera.id,
            "workflow_id": start.workflow_id,
            "revision": start.revision,
            "run_id": start.run_id,
            "model_id": "people",
        }
        fields.update(overrides)

        return make_frame(**fields)

    async def test_matching_frame_runs_the_persisted_graph(
        self, effects, fake_session, basic_graph, make_frame
    ):
        _workflow, camera, start = self.seed(fake_session, basic_graph)

        await handle_detection_frame(self.matching_frame(make_frame, camera, start), effects.frames)

        identity, _event, action, _context = effects.actions[0]

        assert action.kind == "log_alert_action"
        assert identity == ExecutionIdentity(
            workflow_id=start.workflow_id,
            run_id=start.run_id,
            camera_name="Front door",
            node_id="alert",
        )
        assert effects.commands == []

    async def test_frame_for_unknown_camera_stops_its_run(self, effects, make_frame):
        frame = make_frame()

        await handle_detection_frame(frame, effects.frames)

        assert effects.commands == [
            StopStream(camera_id=frame.camera_id, revision=frame.revision, run_id=frame.run_id)
        ]
        assert effects.realtime == []

    async def test_frame_naming_another_workflow_stops_its_run(
        self, effects, fake_session, basic_graph, make_frame
    ):
        _workflow, camera, start = self.seed(fake_session, basic_graph)
        frame = self.matching_frame(make_frame, camera, start, workflow_id=uuid4())

        await handle_detection_frame(frame, effects.frames)

        assert [type(command) for command in effects.commands] == [StopStream]
        assert effects.actions == []

    async def test_frame_for_camera_without_desired_run_stops_it(
        self, effects, fake_session, basic_graph, make_frame
    ):
        _workflow, camera, start = self.seed(fake_session, basic_graph)
        camera.start_command = None

        await handle_detection_frame(self.matching_frame(make_frame, camera, start), effects.frames)

        assert [type(command) for command in effects.commands] == [StopStream]

    async def test_stale_revision_is_dropped_silently(
        self, effects, fake_session, basic_graph, make_frame, caplog
    ):
        _workflow, camera, start = self.seed(fake_session, basic_graph, revision=3)
        caplog.set_level("DEBUG", logger="api.application.frame_processing")

        await handle_detection_frame(
            self.matching_frame(make_frame, camera, start, revision=2), effects.frames
        )

        assert effects.commands == []
        assert effects.realtime == []
        assert "dropping stale frame" in caplog.text

    async def test_frame_from_superseded_run_is_dropped(
        self, effects, fake_session, basic_graph, make_frame
    ):
        _workflow, camera, start = self.seed(fake_session, basic_graph)

        await handle_detection_frame(
            self.matching_frame(make_frame, camera, start, run_id=uuid4()), effects.frames
        )

        assert effects.commands == []
        assert effects.actions == []

    async def test_frame_for_disabled_workflow_is_dropped(
        self, effects, fake_session, basic_graph, make_frame
    ):
        _workflow, camera, start = self.seed(fake_session, basic_graph, enabled=False)

        await handle_detection_frame(self.matching_frame(make_frame, camera, start), effects.frames)

        assert effects.commands == []
        assert effects.actions == []

    async def test_frame_for_missing_model_is_dropped_with_warning(
        self, effects, fake_session, basic_graph, make_frame, caplog
    ):
        _workflow, camera, start = self.seed(fake_session, basic_graph)
        camera.start_command["config"]["model_id"] = "ghost"

        await handle_detection_frame(
            self.matching_frame(make_frame, camera, start, model_id="ghost"), effects.frames
        )

        assert effects.actions == []
        assert "unavailable model=ghost" in caplog.text

    async def test_corrupt_persisted_start_command_drops_the_frame(
        self, effects, fake_session, basic_graph, make_frame
    ):
        _workflow, camera, start = self.seed(fake_session, basic_graph)
        camera.start_command = {"type": "start_stream"}

        await handle_detection_frame(self.matching_frame(make_frame, camera, start), effects.frames)

        assert effects.commands == []
        assert effects.actions == []

    async def test_invalid_persisted_graph_drops_the_frame(
        self, effects, fake_session, basic_graph, make_frame, caplog
    ):
        workflow, camera, start = self.seed(fake_session, basic_graph)
        workflow.graph = {"nodes": "broken"}

        await handle_detection_frame(self.matching_frame(make_frame, camera, start), effects.frames)

        assert effects.actions == []
        assert "invalid persisted runtime state" in caplog.text

    async def test_lookup_failure_is_retryable_without_stopping(
        self, effects, fake_session, make_frame, caplog
    ):
        fake_session.fail_on_execute = RuntimeError("database away")

        with pytest.raises(RetryableFrameError):
            await handle_detection_frame(make_frame(), effects.frames)

        assert effects.commands == []
        assert "camera/workflow lookup failed" in caplog.text
