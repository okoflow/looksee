"""Factories shared by the domain test modules."""

from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from api.domain.events import DetectionEvent
from api.domain.workflow.runtime import FilterRuntime
from shared import Detection

CAMERA_ID = UUID("11111111-1111-4111-8111-111111111111")
WORKFLOW_ID = UUID("22222222-2222-4222-8222-222222222222")
RUN_ID = UUID("33333333-3333-4333-8333-333333333333")
WEDNESDAY_NOON = datetime(2026, 1, 7, 12, 0, tzinfo=UTC)


class RecordingState:
    """RuntimeState double: records every call and answers with fixed values."""

    def __init__(self, *, debounce: bool = True, dwell: float = 0.0) -> None:
        self.debounce = debounce
        self.dwell = dwell
        self.calls: list[tuple[object, ...]] = []

    def swap_track_point(self, workflow_id, run_id, node_id, camera_id, tracker_id, point, now):
        call = ("swap_track_point", workflow_id, run_id, node_id, camera_id, tracker_id, point, now)

        self.calls.append(call)

    def dwell_seconds(self, workflow_id, run_id, node_id, camera_id, tracker_id, inside, now):
        call = ("dwell_seconds", workflow_id, run_id, node_id, camera_id, tracker_id, inside, now)

        self.calls.append(call)

        return self.dwell

    def debounce_allows(self, workflow_id, run_id, node_id, camera_id, seconds):
        call = ("debounce_allows", workflow_id, run_id, node_id, camera_id, seconds)

        self.calls.append(call)

        return self.debounce


@pytest.fixture
def make_detection():
    def _make(**overrides):
        values = {
            "label": "person",
            "bounding_box": (0.0, 0.0, 100.0, 100.0),
            "confidence": 0.9,
            "class_id": 0,
        }

        return Detection(**{**values, **overrides})

    return _make


@pytest.fixture
def make_event():
    def _make(**overrides):
        values = {
            "camera_id": CAMERA_ID,
            "workflow_id": WORKFLOW_ID,
            "model_id": "yolo",
            "kind": "PERSON_DETECTED",
            "ts": WEDNESDAY_NOON,
            "frame_width": 1000,
            "frame_height": 1000,
        }

        return DetectionEvent(**{**values, **overrides})

    return _make


@pytest.fixture
def make_state():
    return RecordingState


@pytest.fixture
def make_runtime():
    def _make(*, state=None, node_id="filter-1", timezone="UTC"):
        return FilterRuntime(
            workflow_id=WORKFLOW_ID,
            run_id=RUN_ID,
            node_id=node_id,
            timezone=ZoneInfo(timezone),
            state=state if state is not None else RecordingState(),
        )

    return _make
