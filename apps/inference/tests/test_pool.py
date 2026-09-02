import asyncio
from uuid import uuid4

import pytest

from inference.application.pool import WorkerPool
from shared import StopStream, WorkerStopped


class FakeWorker:
    def __init__(self, command) -> None:
        self.command = command
        self.started = asyncio.Event()
        self.finished = asyncio.Event()
        self.cancelled = False
        self.error: Exception | None = None
        self.accepts_apply = False
        self.applied = []
        self.replay_calls = 0

    async def run(self) -> None:
        self.started.set()
        if self.error is not None:
            raise self.error

        try:
            await self.finished.wait()
        except asyncio.CancelledError:
            self.cancelled = True
            raise

    async def replay_started(self) -> bool:
        self.replay_calls += 1

        return True

    async def apply(self, command) -> bool:
        self.applied.append(command)

        return self.accepts_apply


class FakeWorkerFactory:
    def __init__(self) -> None:
        self.workers: list[FakeWorker] = []
        self.accepts_apply = False
        self.error: Exception | None = None

    def __call__(self, command) -> FakeWorker:
        worker = FakeWorker(command)
        worker.accepts_apply = self.accepts_apply
        worker.error = self.error
        self.workers.append(worker)

        return worker


class FakeOutput:
    def __init__(self) -> None:
        self.frames = []
        self.events = []

    async def publish_detection_frame(self, frame) -> None:
        self.frames.append(frame)

    async def publish_worker_event(self, event) -> None:
        self.events.append(event)


async def wait_started(worker: FakeWorker) -> None:
    await asyncio.wait_for(worker.started.wait(), timeout=1.0)


@pytest.fixture
def factory() -> FakeWorkerFactory:
    return FakeWorkerFactory()


@pytest.fixture
def output() -> FakeOutput:
    return FakeOutput()


@pytest.fixture
async def pool(factory, output):
    pool = WorkerPool(factory, output)

    yield pool

    await pool.shutdown()


async def test_start_runs_a_worker_for_the_command(pool, factory, make_start_command):
    command = make_start_command()

    await pool.start_camera(command)

    [worker] = factory.workers
    await wait_started(worker)
    assert worker.command == command


async def test_repeating_the_same_start_replays_state_instead_of_restarting(
    pool, factory, make_start_command
):
    command = make_start_command()
    await pool.start_camera(command)

    await pool.start_camera(command)

    [worker] = factory.workers
    assert worker.replay_calls == 1


async def test_stale_start_is_ignored(pool, factory, make_start_command):
    camera_id = uuid4()
    await pool.start_camera(make_start_command(camera_id=camera_id, revision=5))

    await pool.start_camera(make_start_command(camera_id=camera_id, revision=4))

    [worker] = factory.workers
    assert worker.command.revision == 5
    assert worker.applied == []
    assert worker.replay_calls == 0


async def test_conflicting_start_at_same_revision_is_ignored(pool, factory, make_start_command):
    camera_id = uuid4()
    await pool.start_camera(make_start_command(camera_id=camera_id, revision=5))

    await pool.start_camera(make_start_command(camera_id=camera_id, revision=5))

    [worker] = factory.workers
    assert worker.applied == []
    assert worker.replay_calls == 0


async def test_newer_start_is_applied_in_place_when_worker_accepts_it(
    pool, factory, make_start_command
):
    factory.accepts_apply = True
    camera_id = uuid4()
    await pool.start_camera(make_start_command(camera_id=camera_id, revision=1))
    await wait_started(factory.workers[0])
    retarget = make_start_command(camera_id=camera_id, revision=2)

    await pool.start_camera(retarget)

    [worker] = factory.workers
    assert worker.applied == [retarget]
    assert not worker.cancelled


async def test_in_place_apply_makes_the_new_command_the_active_run(
    pool, factory, make_start_command
):
    factory.accepts_apply = True
    camera_id = uuid4()
    await pool.start_camera(make_start_command(camera_id=camera_id, revision=1))
    await wait_started(factory.workers[0])
    retarget = make_start_command(camera_id=camera_id, revision=2)
    await pool.start_camera(retarget)

    await pool.start_camera(retarget)

    [worker] = factory.workers
    assert worker.replay_calls == 1


async def test_newer_start_restarts_worker_that_refuses_in_place_apply(
    pool, factory, make_start_command
):
    camera_id = uuid4()
    await pool.start_camera(make_start_command(camera_id=camera_id, revision=1))
    await wait_started(factory.workers[0])
    retarget = make_start_command(camera_id=camera_id, revision=2)

    await pool.start_camera(retarget)

    old, new = factory.workers
    assert old.applied == [retarget]
    assert old.cancelled
    assert new.command == retarget


async def test_stop_cancels_worker_and_publishes_stopped_event(
    pool, factory, output, make_start_command
):
    command = make_start_command(revision=1)
    await pool.start_camera(command)
    await wait_started(factory.workers[0])

    await pool.stop_camera(StopStream(camera_id=command.camera_id, revision=2))

    [event] = output.events
    assert factory.workers[0].cancelled
    assert isinstance(event, WorkerStopped)
    assert event.camera_id == command.camera_id
    assert event.workflow_id == command.workflow_id
    assert event.run_id == command.run_id
    assert event.model_id == command.config.model_id
    assert event.revision == 2


async def test_stop_for_unknown_camera_publishes_nothing(pool, output):
    await pool.stop_camera(StopStream(camera_id=uuid4(), revision=1))

    assert output.events == []


async def test_stale_stop_is_ignored(pool, factory, output, make_start_command):
    command = make_start_command(revision=3)
    await pool.start_camera(command)
    await wait_started(factory.workers[0])

    await pool.stop_camera(StopStream(camera_id=command.camera_id, revision=2))

    assert not factory.workers[0].cancelled
    assert output.events == []


async def test_targeted_stop_for_another_run_is_ignored(pool, factory, output, make_start_command):
    command = make_start_command(revision=3)
    await pool.start_camera(command)
    await wait_started(factory.workers[0])

    await pool.stop_camera(StopStream(camera_id=command.camera_id, revision=3, run_id=uuid4()))

    assert not factory.workers[0].cancelled
    assert output.events == []


async def test_targeted_stop_for_the_active_run_stops_it(pool, factory, output, make_start_command):
    command = make_start_command(revision=3)
    await pool.start_camera(command)
    await wait_started(factory.workers[0])

    await pool.stop_camera(
        StopStream(camera_id=command.camera_id, revision=3, run_id=command.run_id)
    )

    [event] = output.events
    assert factory.workers[0].cancelled
    assert event.revision == 3


async def test_untargeted_stop_at_same_revision_stops_the_active_run(
    pool, factory, output, make_start_command
):
    command = make_start_command(revision=3)
    await pool.start_camera(command)
    await wait_started(factory.workers[0])

    await pool.stop_camera(StopStream(camera_id=command.camera_id, revision=3))

    assert factory.workers[0].cancelled
    assert len(output.events) == 1


async def test_newer_stop_ignores_its_run_target(pool, factory, output, make_start_command):
    command = make_start_command(revision=3)
    await pool.start_camera(command)
    await wait_started(factory.workers[0])

    await pool.stop_camera(StopStream(camera_id=command.camera_id, revision=4, run_id=uuid4()))

    [event] = output.events
    assert factory.workers[0].cancelled
    assert event.run_id == command.run_id


async def test_repeated_stop_publishes_once(pool, factory, output, make_start_command):
    command = make_start_command(revision=1)
    await pool.start_camera(command)
    await wait_started(factory.workers[0])
    stop = StopStream(camera_id=command.camera_id, revision=2)
    await pool.stop_camera(stop)

    await pool.stop_camera(stop)

    assert len(output.events) == 1


async def test_start_older_than_the_last_stop_is_ignored(pool, factory, make_start_command):
    camera_id = uuid4()
    await pool.stop_camera(StopStream(camera_id=camera_id, revision=5))

    await pool.start_camera(make_start_command(camera_id=camera_id, revision=4))

    assert factory.workers == []


async def test_start_at_the_last_stop_revision_is_ignored(pool, factory, make_start_command):
    camera_id = uuid4()
    await pool.stop_camera(StopStream(camera_id=camera_id, revision=5))

    await pool.start_camera(make_start_command(camera_id=camera_id, revision=5))

    assert factory.workers == []


async def test_start_newer_than_the_last_stop_runs(pool, factory, make_start_command):
    camera_id = uuid4()
    await pool.stop_camera(StopStream(camera_id=camera_id, revision=5))

    await pool.start_camera(make_start_command(camera_id=camera_id, revision=6))

    assert len(factory.workers) == 1


async def test_cameras_are_fenced_independently(pool, factory, make_start_command):
    await pool.start_camera(make_start_command(revision=9))

    await pool.start_camera(make_start_command(revision=1))

    assert len(factory.workers) == 2


async def test_shutdown_cancels_every_worker_without_events(
    pool, factory, output, make_start_command
):
    await pool.start_camera(make_start_command())
    await pool.start_camera(make_start_command())
    for worker in factory.workers:
        await wait_started(worker)

    await pool.shutdown()

    assert [worker.cancelled for worker in factory.workers] == [True, True]
    assert output.events == []


async def test_shutdown_forgets_desired_state(pool, factory, make_start_command):
    camera_id = uuid4()
    await pool.start_camera(make_start_command(camera_id=camera_id, revision=9))
    await pool.shutdown()

    await pool.start_camera(make_start_command(camera_id=camera_id, revision=1))

    assert len(factory.workers) == 2


async def test_finished_worker_is_replaced_on_the_next_start(pool, factory, make_start_command):
    command = make_start_command()
    await pool.start_camera(command)
    finished = factory.workers[0]
    finished.finished.set()
    await wait_started(finished)

    await pool.start_camera(command)

    assert len(factory.workers) == 2
    assert finished.replay_calls == 0


async def test_crashed_worker_is_replaced_on_the_next_start(pool, factory, make_start_command):
    factory.error = RuntimeError("boom")
    command = make_start_command()
    await pool.start_camera(command)
    await wait_started(factory.workers[0])
    factory.error = None

    await pool.start_camera(command)

    assert len(factory.workers) == 2
    assert factory.workers[0].replay_calls == 0
