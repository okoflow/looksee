"""Builders for enterprise filter and delivery tests."""

from datetime import UTC, datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest

from api.adapters.state.memory import InMemoryRuntimeState
from api.application.execution import ExecutionIdentity
from api.domain.events import DetectionEvent
from api.domain.workflow.runtime import FilterRuntime
from shared import Detection

T0 = datetime(2026, 3, 4, 12, 0, tzinfo=UTC)


@pytest.fixture
def make_detection():
    def make(center=(0.5, 0.5), tracker_id=7, label="person"):
        x, y = center[0] * 1000, center[1] * 1000

        return Detection(
            label=label,
            bounding_box=(x - 10, y - 10, x + 10, y + 10),
            confidence=0.9,
            class_id=0,
            tracker_id=tracker_id,
        )

    return make


@pytest.fixture
def make_event(make_detection):
    camera_id, workflow_id = uuid4(), uuid4()

    def make(*detections, ts=T0, kind="PERSON_DETECTED"):
        return DetectionEvent(
            camera_id=camera_id,
            workflow_id=workflow_id,
            model_id="people",
            kind=kind,
            ts=ts,
            frame_width=1000,
            frame_height=1000,
            detections=list(detections) if detections else [make_detection()],
            metadata={"count": len(detections) or 1},
        )

    return make


@pytest.fixture
def runtime():
    return FilterRuntime(
        workflow_id=uuid4(),
        run_id=uuid4(),
        node_id="filter",
        timezone=ZoneInfo("UTC"),
        state=InMemoryRuntimeState(),
    )


@pytest.fixture
def identity():
    return ExecutionIdentity(
        workflow_id=uuid4(), run_id=uuid4(), camera_name="Dock", node_id="slack"
    )
