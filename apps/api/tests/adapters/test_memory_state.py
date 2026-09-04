"""Process-local runtime windows: retries, track points, dwell, debounce, cooldown."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from api.adapters.state.memory import InMemoryRuntimeState

T0 = datetime(2026, 3, 4, 12, 0, tzinfo=UTC)


@pytest.fixture
def state():
    return InMemoryRuntimeState()


@pytest.fixture
def track_key():
    return (uuid4(), uuid4(), "node", uuid4())


def test_retry_backoff_doubles_up_to_the_cap(state):
    camera = uuid4()
    delays = []

    for _attempt in range(4):
        state.note_worker_retry(camera, 1, T0, base_seconds=30, cap_seconds=100)
        ready_at = next(
            seconds
            for seconds in range(0, 400, 5)
            if state.worker_retry_ready(camera, 1, T0 + timedelta(seconds=seconds))
        )
        delays.append(ready_at)

    assert delays == [30, 60, 100, 100]


def test_retry_window_resets_for_a_new_revision_and_on_clear(state):
    camera = uuid4()
    state.note_worker_retry(camera, 1, T0, base_seconds=30, cap_seconds=300)

    blocked = state.worker_retry_ready(camera, 1, T0)
    other_revision = state.worker_retry_ready(camera, 2, T0)
    state.clear_worker_retry(camera)

    assert blocked is False
    assert other_revision is True
    assert state.worker_retry_ready(camera, 1, T0) is True


def test_track_point_swap_returns_the_previous_recent_point(state, track_key):
    first = state.swap_track_point(*track_key, 7, (0.1, 0.1), T0)
    second = state.swap_track_point(*track_key, 7, (0.2, 0.2), T0 + timedelta(seconds=1))
    other_tracker = state.swap_track_point(*track_key, 8, (0.9, 0.9), T0 + timedelta(seconds=1))

    assert first is None
    assert second == (0.1, 0.1)
    assert other_tracker is None


def test_out_of_order_track_point_is_ignored(state, track_key):
    state.swap_track_point(*track_key, 7, (0.5, 0.5), T0 + timedelta(seconds=5))

    stale = state.swap_track_point(*track_key, 7, (0.1, 0.1), T0)
    latest = state.swap_track_point(*track_key, 7, (0.6, 0.6), T0 + timedelta(seconds=6))

    assert stale is None
    assert latest == (0.5, 0.5)


def test_track_point_older_than_a_minute_is_forgotten(state, track_key):
    state.swap_track_point(*track_key, 7, (0.1, 0.1), T0)

    assert state.swap_track_point(*track_key, 7, (0.2, 0.2), T0 + timedelta(seconds=61)) is None


def test_dwell_accumulates_while_inside_and_resets_on_exit(state, track_key):
    entered = state.dwell_seconds(*track_key, 7, True, T0)
    later = state.dwell_seconds(*track_key, 7, True, T0 + timedelta(seconds=45))
    left = state.dwell_seconds(*track_key, 7, False, T0 + timedelta(seconds=50))
    back = state.dwell_seconds(*track_key, 7, True, T0 + timedelta(seconds=51))

    assert (entered, later, left, back) == (0.0, 45.0, 0.0, 0.0)


def test_dwell_restarts_after_the_track_went_unseen_too_long(state, track_key):
    state.dwell_seconds(*track_key, 7, True, T0)

    assert state.dwell_seconds(*track_key, 7, True, T0 + timedelta(seconds=90)) == 0.0


def test_debounce_allows_once_per_window_per_node(state):
    workflow, run, camera = uuid4(), uuid4(), uuid4()

    first = state.debounce_allows(workflow, run, "a", camera, 30)
    repeat = state.debounce_allows(workflow, run, "a", camera, 30)
    other_node = state.debounce_allows(workflow, run, "b", camera, 30)

    assert (first, repeat, other_node) == (True, False, True)


def test_event_cooldown_is_per_camera_run_and_kind(state):
    camera, run = uuid4(), uuid4()
    state.touch_event_cooldown(camera, run, "PERSON_DETECTED")

    assert state.event_cooldown_ready(camera, run, "PERSON_DETECTED", 2.0) is False
    assert state.event_cooldown_ready(camera, run, "CAR_DETECTED", 2.0) is True
    assert state.event_cooldown_ready(camera, uuid4(), "PERSON_DETECTED", 2.0) is True


@pytest.mark.parametrize("seconds", [0.0, -1.0])
def test_non_positive_cooldown_is_always_ready(state, seconds):
    camera, run = uuid4(), uuid4()
    state.touch_event_cooldown(camera, run, "PERSON_DETECTED")

    assert state.event_cooldown_ready(camera, run, "PERSON_DETECTED", seconds) is True


def test_worker_retry_remains_bounded_after_months_offline(state):
    camera = uuid4()

    for _ in range(2000):
        state.note_worker_retry(camera, 1, T0, base_seconds=30, cap_seconds=300)

    assert not state.worker_retry_ready(camera, 1, T0 + timedelta(seconds=299))
    assert state.worker_retry_ready(camera, 1, T0 + timedelta(seconds=300))


def test_out_of_order_exit_does_not_erase_dwell(state, track_key):
    state.dwell_seconds(*track_key, 7, True, T0)
    state.dwell_seconds(*track_key, 7, True, T0 + timedelta(seconds=20))
    state.dwell_seconds(*track_key, 7, False, T0 + timedelta(seconds=10))

    assert state.dwell_seconds(*track_key, 7, True, T0 + timedelta(seconds=30)) == 30


def test_failed_transaction_restores_track_and_debounce_state(state, track_key):
    state.swap_track_point(*track_key, 7, (0.1, 0.1), T0)

    with pytest.raises(RuntimeError), state.transaction():
        state.swap_track_point(*track_key, 7, (0.9, 0.9), T0 + timedelta(seconds=1))
        assert state.debounce_allows(*track_key, 30)
        raise RuntimeError("queue unavailable")

    assert state.swap_track_point(*track_key, 7, (0.9, 0.9), T0 + timedelta(seconds=1)) == (
        0.1,
        0.1,
    )
    assert state.debounce_allows(*track_key, 30)


def test_successful_transaction_keeps_state(state, track_key):
    with state.transaction():
        assert state.debounce_allows(*track_key, 30)

    assert not state.debounce_allows(*track_key, 30)
