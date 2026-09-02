"""Deriving semantic events from one labelled detection frame."""

from api.application.events import derive_events


def test_detections_are_grouped_into_one_event_per_kind(make_frame, make_detection, people_model):
    frame = make_frame(
        detections=(
            make_detection(label="person"),
            make_detection(label="car", class_id=1),
            make_detection(label="person"),
        )
    )

    events = derive_events(frame, people_model)

    assert [event.kind for event in events] == ["PERSON_DETECTED", "CAR_DETECTED"]
    assert [len(event.detections) for event in events] == [2, 1]
    assert events[0].metadata == {"count": 2, "model_id": "people"}


def test_labels_without_an_event_kind_are_dropped(make_frame, make_detection, people_model):
    frame = make_frame(
        detections=(make_detection(label="background", class_id=2), make_detection(label="alien"))
    )

    assert derive_events(frame, people_model) == []


def test_empty_frame_yields_no_events(make_frame, people_model):
    assert derive_events(make_frame(detections=()), people_model) == []


def test_event_copies_frame_identity_and_geometry(make_frame, people_model):
    frame = make_frame()

    event = derive_events(frame, people_model)[0]

    assert event.camera_id == frame.camera_id
    assert event.workflow_id == frame.workflow_id
    assert event.model_id == "people"
    assert event.ts == frame.timestamp
    assert (event.frame_width, event.frame_height) == (frame.frame_width, frame.frame_height)
    assert event.detections == list(frame.detections)
