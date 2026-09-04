"""Process-local runtime windows and per-track state."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from math import ceil, log2
from typing import Any
from uuid import UUID

from shared import EventKind

type _TrackKey = tuple[UUID, UUID, str, UUID, int]

_TRACK_STALE_SECONDS = 60.0
_WINDOW_STALE_SECONDS = 2 * 3600.0
_PRUNE_THRESHOLD = 4096
_MISSING = object()


class InMemoryRuntimeState:
    def __init__(self) -> None:
        self._debounce: dict[tuple[UUID, UUID, str, UUID], datetime] = {}
        self._event_cooldown: dict[tuple[UUID, UUID, EventKind], datetime] = {}
        self._track_points: dict[_TrackKey, tuple[datetime, tuple[float, float]]] = {}
        self._dwell_entries: dict[_TrackKey, tuple[datetime, datetime]] = {}
        self._worker_retries: dict[UUID, tuple[int, int, datetime]] = {}
        self._undo: list[tuple[dict, Any, Any]] | None = None

    @contextmanager
    def transaction(self) -> Iterator[None]:
        if self._undo is not None:
            raise RuntimeError("runtime state transactions cannot overlap")

        self._undo = []
        try:
            yield
        except BaseException:
            for store, key, previous in reversed(self._undo):
                if previous is _MISSING:
                    store.pop(key, None)
                else:
                    store[key] = previous
            raise
        finally:
            self._undo = None

    def _set[K, V](self, store: dict[K, V], key: K, value: V) -> None:
        if self._undo is not None:
            self._undo.append((store, key, store.get(key, _MISSING)))
        store[key] = value

    def _discard[K, V](self, store: dict[K, V], key: K) -> None:
        if self._undo is not None:
            self._undo.append((store, key, store.get(key, _MISSING)))
        store.pop(key, None)

    def worker_retry_ready(self, camera_id: UUID, revision: int, now: datetime) -> bool:
        entry = self._worker_retries.get(camera_id)
        if entry is None:
            return True

        entry_revision, _attempts, next_attempt_at = entry
        if revision != entry_revision:
            return True

        return now >= next_attempt_at

    def note_worker_retry(
        self,
        camera_id: UUID,
        revision: int,
        now: datetime,
        base_seconds: float,
        cap_seconds: float,
    ) -> None:
        entry = self._worker_retries.get(camera_id)

        attempts = 0
        if entry is not None and entry[0] == revision:
            attempts = entry[1]

        # Clamp before exponentiation: an offline camera can retry for months.
        max_attempts = max(0, ceil(log2(max(1.0, cap_seconds / base_seconds))))
        attempts = min(attempts, max_attempts)
        delay = min(base_seconds * (2.0**attempts), cap_seconds)
        self._worker_retries[camera_id] = (
            revision,
            min(attempts + 1, max_attempts),
            now + timedelta(seconds=delay),
        )

    def clear_worker_retry(self, camera_id: UUID) -> None:
        self._worker_retries.pop(camera_id, None)

    def swap_track_point(
        self,
        workflow_id: UUID,
        run_id: UUID,
        node_id: str,
        camera_id: UUID,
        tracker_id: int,
        point: tuple[float, float],
        now: datetime,
    ) -> tuple[float, float] | None:
        key = (workflow_id, run_id, node_id, camera_id, tracker_id)
        previous = self._track_points.get(key)
        if previous is not None and now < previous[0]:
            return None

        self._set(self._track_points, key, (now, point))
        self._prune_stale(self._track_points, now, 0)

        if previous is None:
            return None

        age_seconds = (now - previous[0]).total_seconds()
        if age_seconds > _TRACK_STALE_SECONDS:
            return None

        return previous[1]

    def dwell_seconds(
        self,
        workflow_id: UUID,
        run_id: UUID,
        node_id: str,
        camera_id: UUID,
        tracker_id: int,
        inside: bool,
        now: datetime,
    ) -> float:
        key = (workflow_id, run_id, node_id, camera_id, tracker_id)

        entry = self._dwell_entries.get(key)
        if entry is not None and now < entry[1]:
            return 0.0

        if not inside:
            self._discard(self._dwell_entries, key)

            return 0.0

        if entry is None or (now - entry[1]).total_seconds() > _TRACK_STALE_SECONDS:
            self._set(self._dwell_entries, key, (now, now))
            self._prune_stale(self._dwell_entries, now, 1)

            return 0.0

        entered_at, _last_seen = entry
        self._set(self._dwell_entries, key, (entered_at, now))

        return (now - entered_at).total_seconds()

    def debounce_allows(
        self,
        workflow_id: UUID,
        run_id: UUID,
        node_id: str,
        camera_id: UUID,
        seconds: int,
    ) -> bool:
        now = datetime.now(UTC)
        key = (workflow_id, run_id, node_id, camera_id)

        last = self._debounce.get(key)
        if last is not None and (now - last).total_seconds() < seconds:
            return False

        self._set(self._debounce, key, now)
        self._prune_timestamps(self._debounce, now)

        return True

    def event_cooldown_ready(
        self,
        camera_id: UUID,
        run_id: UUID,
        kind: EventKind,
        seconds: float,
    ) -> bool:
        if seconds <= 0:
            return True

        last = self._event_cooldown.get((camera_id, run_id, kind))

        return last is None or (datetime.now(UTC) - last).total_seconds() >= seconds

    def touch_event_cooldown(self, camera_id: UUID, run_id: UUID, kind: EventKind) -> None:
        now = datetime.now(UTC)
        self._set(self._event_cooldown, (camera_id, run_id, kind), now)
        self._prune_timestamps(self._event_cooldown, now)

    @staticmethod
    def _prune_timestamps[K](store: dict[K, datetime], now: datetime) -> None:
        _prune_stale_keys(
            store,
            lambda timestamp: (now - timestamp).total_seconds() > _WINDOW_STALE_SECONDS,
        )

    @staticmethod
    def _prune_stale[V: tuple](
        store: dict[_TrackKey, V],
        now: datetime,
        seen_index: int,
    ) -> None:
        _prune_stale_keys(
            store,
            lambda value: (now - value[seen_index]).total_seconds() > _TRACK_STALE_SECONDS,
        )


def _prune_stale_keys[K, V](store: dict[K, V], is_stale: Callable[[V], bool]) -> None:
    if len(store) < _PRUNE_THRESHOLD:
        return

    stale = [key for key, value in store.items() if is_stale(value)]
    for key in stale:
        del store[key]


runtime_state = InMemoryRuntimeState()
