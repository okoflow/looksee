import numpy as np
import pytest
import supervision as sv

from inference.adapters.tracking import ByteTrackDetectionTracker

FRAME_RATE = 5.0


def detections_of(boxes, confidence, class_ids) -> sv.Detections:
    return sv.Detections(
        xyxy=np.asarray(boxes, dtype=np.float32),
        confidence=np.asarray(confidence, dtype=np.float32),
        class_id=np.asarray(class_ids, dtype=np.int64),
    )


def two_objects(shift: int = 0) -> sv.Detections:
    boxes = np.array([[10, 10, 50, 50], [100, 100, 160, 180]]) + shift

    return detections_of(boxes, [0.9, 0.8], [0, 1])


@pytest.fixture
def tracker() -> ByteTrackDetectionTracker:
    return ByteTrackDetectionTracker(frame_rate=FRAME_RATE)


def test_first_observation_leaves_detections_untracked(tracker):
    tracked = tracker.update(two_objects())

    assert tracked.tracker_id.tolist() == [-1, -1]


def test_ids_confirm_on_the_first_matched_frame(tracker):
    tracker.update(two_objects())

    tracked = tracker.update(two_objects())

    assert (tracked.tracker_id >= 0).all()
    assert len(set(tracked.tracker_id.tolist())) == 2


def test_ids_follow_moving_objects(tracker):
    tracker.update(two_objects())
    confirmed = tracker.update(two_objects())

    moved = tracker.update(two_objects(shift=5))

    assert moved.tracker_id.tolist() == confirmed.tracker_id.tolist()


def test_ids_follow_objects_when_detector_order_changes(tracker):
    tracker.update(two_objects())
    confirmed = tracker.update(two_objects())

    reordered = tracker.update(two_objects(shift=8)[[1, 0]])

    assert reordered.tracker_id.tolist() == confirmed.tracker_id.tolist()[::-1]


def test_preserves_detector_rows_and_order(tracker):
    source = two_objects()

    tracked = tracker.update(source)

    assert tracked.xyxy.tolist() == source.xyxy.tolist()
    assert tracked.confidence.tolist() == source.confidence.tolist()
    assert tracked.class_id.tolist() == source.class_id.tolist()
    assert tracked.tracker_id.dtype == np.int64


def test_low_confidence_detections_never_start_tracks(tracker):
    low = detections_of([[300, 300, 340, 340]], [0.3], [2])
    tracker.update(low)

    tracked = tracker.update(low)

    assert tracked.tracker_id.tolist() == [-1]


def test_empty_detections_yield_empty_ids(tracker):
    tracked = tracker.update(sv.Detections.empty())

    assert len(tracked) == 0
    assert tracked.tracker_id.tolist() == []


def test_id_survives_a_missed_frame(tracker):
    one = detections_of([[10, 10, 50, 50]], [0.9], [0])
    tracker.update(one)
    [confirmed_id] = tracker.update(one).tracker_id.tolist()
    tracker.update(sv.Detections.empty())

    returned = tracker.update(one)

    assert returned.tracker_id.tolist() == [confirmed_id]


def test_new_object_gets_a_fresh_id(tracker):
    one = detections_of([[10, 10, 50, 50]], [0.9], [0])
    far = detections_of([[400, 400, 440, 440]], [0.9], [0])
    tracker.update(one)
    [first_id] = tracker.update(one).tracker_id.tolist()
    tracker.update(far)

    tracked = tracker.update(far)

    assert tracked.tracker_id[0] >= 0
    assert tracked.tracker_id[0] != first_id
