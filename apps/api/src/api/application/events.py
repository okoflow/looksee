"""Derive semantic workflow events from one labelled perception frame."""

from collections import defaultdict

from api.domain.events import DetectionEvent
from api.domain.models import ModelDescriptor
from shared import Detection, DetectionFrame, EventKind


def derive_events(frame: DetectionFrame, model: ModelDescriptor) -> list[DetectionEvent]:
    event_by_label = model.events_by_label()

    detections_by_kind: dict[EventKind, list[Detection]] = defaultdict(list)
    for detection in frame.detections:
        event_kind = event_by_label.get(detection.label)
        if event_kind is not None:
            detections_by_kind[event_kind].append(detection)

    return [
        DetectionEvent(
            camera_id=frame.camera_id,
            workflow_id=frame.workflow_id,
            model_id=model.id,
            kind=event_kind,
            ts=frame.timestamp,
            frame_width=frame.frame_width,
            frame_height=frame.frame_height,
            detections=detections,
            metadata={"count": len(detections), "model_id": model.id},
        )
        for event_kind, detections in detections_by_kind.items()
    ]
