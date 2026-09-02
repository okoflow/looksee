import asyncio
from dataclasses import replace
from datetime import UTC
from uuid import uuid4

import numpy as np
import pytest
import supervision as sv

from inference.application.worker import CameraWorker, WorkerDependencies, run_identity_fields
from shared import Detection, DetectionFrame, WorkerErrored, WorkerStarted, WorkflowConfig

FRAME = np.zeros((48, 64, 3), dtype=np.uint8)
LABELS = {0: "head", 1: "helmet"}


def detections_of(boxes, confidence, class_ids) -> sv.Detections:
    return sv.Detections(
        xyxy=np.asarray(boxes, dtype=np.float32),
        confidence=np.asarray(confidence, dtype=np.float32),
        class_id=np.asarray(class_ids, dtype=np.int64),
    )


class FakeDetector:
    def __init__(self, detections: sv.Detections) -> None:
        self.detections = detections
        self.error: Exception | None = None

    def label_for(self, class_id: int) -> str:
        return LABELS[class_id]

    def detect(self, frame: np.ndarray) -> sv.Detections:
        if self.error is not None:
            raise self.error

        return self.detections


class FakeRegistry:
    def __init__(self, detector: FakeDetector) -> None:
        self.detector = detector
        self.requested: list[str] = []
        self.error: Exception | None = None

    async def get(self, model_id: str) -> FakeDetector:
        self.requested.append(model_id)
        if self.error is not None:
            raise self.error

        return self.detector


class FakeFrameSource:
    def __init__(self) -> None:
        self.frames: asyncio.Queue[np.ndarray] = asyncio.Queue()
        self.started = False
        self.stopped = False
        self.target_fps: list[int] = []
        self.stop_error: Exception | None = None

    def start(self) -> None:
        self.started = True

    def set_target_fps(self, target_fps: int) -> None:
        self.target_fps.append(target_fps)

    async def next_frame(self) -> np.ndarray:
        return await self.frames.get()

    async def stop(self) -> None:
        self.stopped = True
        if self.stop_error is not None:
            raise self.stop_error


class FakeFrameSourceFactory:
    def __init__(self) -> None:
        self.source = FakeFrameSource()
        self.created = []
        self.error: Exception | None = None

    def create(self, camera_id, target_fps: int) -> FakeFrameSource:
        self.created.append((camera_id, target_fps))
        if self.error is not None:
            raise self.error

        return self.source


class FakeOutput:
    def __init__(self) -> None:
        self.frames: list[DetectionFrame] = []
        self.events = []
        self.fail_on: type | None = None
        self._changed = asyncio.Condition()

    async def publish_detection_frame(self, frame: DetectionFrame) -> None:
        await self._record(self.frames, frame)

    async def publish_worker_event(self, event) -> None:
        if self.fail_on is not None and isinstance(event, self.fail_on):
            raise RuntimeError("redis down")

        await self._record(self.events, event)

    async def wait_for_frames(self, count: int) -> None:
        async with asyncio.timeout(2.0), self._changed:
            await self._changed.wait_for(lambda: len(self.frames) >= count)

    async def _record(self, sink: list, item) -> None:
        async with self._changed:
            sink.append(item)
            self._changed.notify_all()


class FakeLastFrames:
    def __init__(self) -> None:
        self.puts = []

    async def put(self, camera_id, jpeg: bytes) -> None:
        self.puts.append((camera_id, jpeg))


class FakeTracker:
    def __init__(self) -> None:
        self.updates: list[sv.Detections] = []
        self.tracker_ids: list[int] | None = None

    def update(self, detections: sv.Detections) -> sv.Detections:
        self.updates.append(detections)
        if self.tracker_ids is None:
            return detections

        return sv.Detections(
            xyxy=detections.xyxy,
            confidence=detections.confidence,
            class_id=detections.class_id,
            tracker_id=np.asarray(self.tracker_ids, dtype=np.int64),
        )


class FakeTrackerFactory:
    def __init__(self) -> None:
        self.tracker = FakeTracker()
        self.frame_rates: list[float] = []

    def __call__(self, frame_rate: float) -> FakeTracker:
        self.frame_rates.append(frame_rate)

        return self.tracker


@pytest.fixture
def detector() -> FakeDetector:
    return FakeDetector(detections_of([[10, 20, 30, 40], [0, 0, 5, 5]], [0.75, 0.25], [1, 0]))


@pytest.fixture
def deps(detector) -> WorkerDependencies:
    return WorkerDependencies(
        models=FakeRegistry(detector),
        frame_sources=FakeFrameSourceFactory(),
        output=FakeOutput(),
        last_frames=FakeLastFrames(),
        encode_jpeg=lambda frame: b"jpeg",
        tracker_factory=FakeTrackerFactory(),
        first_frame_timeout_seconds=5.0,
    )


@pytest.fixture
async def run_worker():
    tasks: list[asyncio.Task[None]] = []

    def start(worker: CameraWorker) -> asyncio.Task[None]:
        task = asyncio.create_task(worker.run())
        tasks.append(task)

        return task

    yield start

    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


def test_run_identity_fields_copies_command_identity_with_a_utc_timestamp(make_start_command):
    command = make_start_command(revision=4)

    fields = run_identity_fields(command)

    assert fields["timestamp"].tzinfo is UTC
    assert fields["revision"] == 4
    assert fields["model_id"] == "dfine-m-ppe"
    assert (fields["camera_id"], fields["workflow_id"], fields["run_id"]) == (
        command.camera_id,
        command.workflow_id,
        command.run_id,
    )


def test_run_identity_fields_overrides_revision(make_start_command):
    command = make_start_command(revision=4)

    fields = run_identity_fields(command, revision=9)

    assert fields["revision"] == 9
    assert WorkerStarted(**fields).revision == 9


async def test_publishes_started_event_with_run_identity(deps, make_start_command, run_worker):
    command = make_start_command()
    deps.frame_sources.source.frames.put_nowait(FRAME)

    run_worker(CameraWorker(command, deps))
    await deps.output.wait_for_frames(1)

    [started] = deps.output.events
    assert isinstance(started, WorkerStarted)
    assert (started.camera_id, started.workflow_id) == (command.camera_id, command.workflow_id)
    assert (started.revision, started.run_id) == (command.revision, command.run_id)
    assert started.model_id == "dfine-m-ppe"


async def test_publishes_detection_frame_with_dimensions_and_identity(
    deps, make_start_command, run_worker
):
    command = make_start_command()
    deps.frame_sources.source.frames.put_nowait(FRAME)

    run_worker(CameraWorker(command, deps))
    await deps.output.wait_for_frames(1)

    [frame] = deps.output.frames
    assert (frame.frame_width, frame.frame_height) == (64, 48)
    assert (frame.camera_id, frame.run_id, frame.revision) == (
        command.camera_id,
        command.run_id,
        command.revision,
    )


async def test_filters_detections_below_threshold_before_tracking(
    deps, make_start_command, run_worker
):
    config = WorkflowConfig(model_id="dfine-m-ppe", confidence_threshold=0.5)
    deps.frame_sources.source.frames.put_nowait(FRAME)

    run_worker(CameraWorker(make_start_command(config=config), deps))
    await deps.output.wait_for_frames(1)

    [tracked] = deps.tracker_factory.tracker.updates
    [frame] = deps.output.frames
    assert tracked.class_id.tolist() == [1]
    assert [detection.label for detection in frame.detections] == ["helmet"]


async def test_maps_tracked_detections_onto_the_wire_schema(deps, make_start_command, run_worker):
    deps.tracker_factory.tracker.tracker_ids = [7]
    deps.frame_sources.source.frames.put_nowait(FRAME)

    run_worker(CameraWorker(make_start_command(), deps))
    await deps.output.wait_for_frames(1)

    [frame] = deps.output.frames
    assert frame.detections == (
        Detection(
            label="helmet",
            bounding_box=(10.0, 20.0, 30.0, 40.0),
            confidence=0.75,
            class_id=1,
            tracker_id=7,
        ),
    )


@pytest.mark.parametrize("tracker_ids", [None, [-1]])
async def test_untracked_detections_carry_no_tracker_id(
    deps, make_start_command, run_worker, tracker_ids
):
    deps.tracker_factory.tracker.tracker_ids = tracker_ids
    deps.frame_sources.source.frames.put_nowait(FRAME)

    run_worker(CameraWorker(make_start_command(), deps))
    await deps.output.wait_for_frames(1)

    [frame] = deps.output.frames
    assert frame.detections[0].tracker_id is None


async def test_publishes_empty_detections_when_nothing_is_found(
    deps, detector, make_start_command, run_worker
):
    detector.detections = sv.Detections.empty()
    deps.frame_sources.source.frames.put_nowait(FRAME)

    run_worker(CameraWorker(make_start_command(), deps))
    await deps.output.wait_for_frames(1)

    [frame] = deps.output.frames
    assert frame.detections == ()


async def test_stores_the_latest_jpeg_for_the_camera(deps, make_start_command, run_worker):
    command = make_start_command()
    deps.frame_sources.source.frames.put_nowait(FRAME)

    run_worker(CameraWorker(command, deps))
    await deps.output.wait_for_frames(1)

    assert deps.last_frames.puts == [(command.camera_id, b"jpeg")]


async def test_skips_last_frame_store_when_encoding_fails(deps, make_start_command, run_worker):
    silent = replace(deps, encode_jpeg=lambda frame: None)
    deps.frame_sources.source.frames.put_nowait(FRAME)

    run_worker(CameraWorker(make_start_command(), silent))
    await deps.output.wait_for_frames(1)

    assert deps.last_frames.puts == []


async def test_wires_model_frame_source_and_tracker_from_config(
    deps, make_start_command, run_worker
):
    config = WorkflowConfig(model_id="dfine-m-ppe", inference_fps=5)
    command = make_start_command(config=config)
    deps.frame_sources.source.frames.put_nowait(FRAME)

    run_worker(CameraWorker(command, deps))
    await deps.output.wait_for_frames(1)

    assert deps.models.requested == ["dfine-m-ppe"]
    assert deps.frame_sources.created == [(command.camera_id, 5)]
    assert deps.frame_sources.source.started
    assert deps.tracker_factory.frame_rates == [5.0]


async def test_reports_missing_first_frame_and_stops_the_source(
    deps, make_start_command, run_worker
):
    impatient = replace(deps, first_frame_timeout_seconds=0.05)
    command = make_start_command()

    await run_worker(CameraWorker(command, impatient))

    [errored] = deps.output.events
    assert isinstance(errored, WorkerErrored)
    assert errored.reason == "no frames from stream within 0.05s"
    assert errored.run_id == command.run_id
    assert deps.frame_sources.source.stopped


async def test_reports_stalled_stream_after_first_frame(deps, make_start_command, run_worker):
    impatient = replace(deps, first_frame_timeout_seconds=0.05)
    deps.frame_sources.source.frames.put_nowait(FRAME)

    await run_worker(CameraWorker(make_start_command(), impatient))

    started, errored = deps.output.events
    assert isinstance(started, WorkerStarted)
    assert isinstance(errored, WorkerErrored)
    assert errored.reason == "no frames from stream for 0.05s"
    assert len(deps.output.frames) == 1


async def test_reports_model_load_failure_without_opening_the_stream(
    deps, make_start_command, run_worker
):
    deps.models.error = FileNotFoundError("model file not found")

    await run_worker(CameraWorker(make_start_command(), deps))

    [errored] = deps.output.events
    assert errored.reason == "model load failed: dfine-m-ppe"
    assert deps.frame_sources.created == []


async def test_reports_frame_source_setup_failure(deps, make_start_command, run_worker):
    deps.frame_sources.error = RuntimeError("mediamtx unreachable")

    await run_worker(CameraWorker(make_start_command(), deps))

    [errored] = deps.output.events
    assert errored.reason == "mediamtx unreachable"


async def test_reports_detector_failure_and_stops_the_source(
    deps, detector, make_start_command, run_worker
):
    detector.error = RuntimeError("cuda out of memory")
    deps.frame_sources.source.frames.put_nowait(FRAME)

    await run_worker(CameraWorker(make_start_command(), deps))

    started, errored = deps.output.events
    assert isinstance(started, WorkerStarted)
    assert errored.reason == "cuda out of memory"
    assert deps.frame_sources.source.stopped
    assert deps.output.frames == []


async def test_names_the_exception_type_when_its_message_is_empty(
    deps, detector, make_start_command, run_worker
):
    detector.error = RuntimeError()
    deps.frame_sources.source.frames.put_nowait(FRAME)

    await run_worker(CameraWorker(make_start_command(), deps))

    assert deps.output.events[-1].reason == "inference failed: RuntimeError"


async def test_truncates_long_failure_reasons(deps, detector, make_start_command, run_worker):
    detector.error = RuntimeError("x" * 300)
    deps.frame_sources.source.frames.put_nowait(FRAME)

    await run_worker(CameraWorker(make_start_command(), deps))

    assert deps.output.events[-1].reason == "x" * 200


async def test_reports_detector_output_without_confidence(
    deps, detector, make_start_command, run_worker
):
    detector.detections = sv.Detections(xyxy=np.zeros((1, 4), dtype=np.float32))
    deps.frame_sources.source.frames.put_nowait(FRAME)

    await run_worker(CameraWorker(make_start_command(), deps))

    reason = deps.output.events[-1].reason
    assert reason == "detections are missing confidence; model adapters must always set it"


async def test_cancellation_stops_the_source_without_an_error_event(
    deps, make_start_command, run_worker
):
    deps.frame_sources.source.frames.put_nowait(FRAME)
    task = run_worker(CameraWorker(make_start_command(), deps))
    await deps.output.wait_for_frames(1)

    task.cancel()
    await asyncio.wait([task])

    assert task.cancelled()
    assert deps.frame_sources.source.stopped
    assert [type(event) for event in deps.output.events] == [WorkerStarted]


async def test_survives_frame_source_cleanup_failure(deps, make_start_command, run_worker):
    impatient = replace(deps, first_frame_timeout_seconds=0.05)
    deps.frame_sources.source.stop_error = RuntimeError("already closed")

    await run_worker(CameraWorker(make_start_command(), impatient))

    [errored] = deps.output.events
    assert isinstance(errored, WorkerErrored)


async def test_survives_errored_event_publish_failure(
    deps, detector, make_start_command, run_worker
):
    detector.error = RuntimeError("boom")
    deps.output.fail_on = WorkerErrored
    deps.frame_sources.source.frames.put_nowait(FRAME)

    await run_worker(CameraWorker(make_start_command(), deps))

    assert [type(event) for event in deps.output.events] == [WorkerStarted]


async def test_replay_is_refused_before_the_worker_is_running(deps, make_start_command):
    worker = CameraWorker(make_start_command(), deps)

    replayed = await worker.replay_started()

    assert replayed is False
    assert deps.output.events == []


async def test_replay_republishes_started_event_while_running(deps, make_start_command, run_worker):
    deps.frame_sources.source.frames.put_nowait(FRAME)
    worker = CameraWorker(make_start_command(), deps)
    run_worker(worker)
    await deps.output.wait_for_frames(1)

    replayed = await worker.replay_started()

    assert replayed is True
    assert [type(event) for event in deps.output.events] == [WorkerStarted, WorkerStarted]


async def test_replay_is_refused_after_the_worker_stopped(deps, make_start_command, run_worker):
    impatient = replace(deps, first_frame_timeout_seconds=0.05)
    worker = CameraWorker(make_start_command(), impatient)
    await run_worker(worker)

    replayed = await worker.replay_started()

    assert replayed is False


async def test_apply_rejects_a_different_model(deps, make_start_command, run_worker):
    camera_id = uuid4()
    deps.frame_sources.source.frames.put_nowait(FRAME)
    worker = CameraWorker(make_start_command(camera_id=camera_id), deps)
    run_worker(worker)
    await deps.output.wait_for_frames(1)
    config = WorkflowConfig(model_id="dfine-m-fire")

    applied = await worker.apply(make_start_command(camera_id=camera_id, revision=2, config=config))

    assert applied is False
    assert deps.frame_sources.source.target_fps == []


async def test_apply_rejects_a_worker_that_is_not_running(deps, make_start_command):
    worker = CameraWorker(make_start_command(), deps)

    applied = await worker.apply(make_start_command(revision=2))

    assert applied is False
    assert deps.output.events == []


async def test_apply_retargets_the_running_worker_in_place(deps, make_start_command, run_worker):
    camera_id = uuid4()
    deps.frame_sources.source.frames.put_nowait(FRAME)
    worker = CameraWorker(make_start_command(camera_id=camera_id), deps)
    run_worker(worker)
    await deps.output.wait_for_frames(1)
    config = WorkflowConfig(model_id="dfine-m-ppe", confidence_threshold=0.1, inference_fps=5)
    retarget = make_start_command(camera_id=camera_id, revision=2, config=config)

    applied = await worker.apply(retarget)
    deps.frame_sources.source.frames.put_nowait(FRAME)
    await deps.output.wait_for_frames(2)

    first, second = deps.output.frames
    assert applied is True
    assert deps.frame_sources.source.target_fps == [5]
    assert deps.output.events[-1].run_id == retarget.run_id
    assert (second.run_id, second.revision) == (retarget.run_id, 2)
    assert (len(first.detections), len(second.detections)) == (1, 2)
