"""Tracking adapter for the external ByteTrack implementation."""

import numpy as np
import supervision as sv
from trackers import ByteTrackTracker

_SOURCE_INDEX_KEY = "inference_source_index"

# ByteTrack scales its lost-track window by frame_rate / 30, so the buffer is
# expressed in reference-fps frames to keep ~3s of track memory at any
# inference fps; at 1 fps the default 30 collapses to a single missed frame.
_LOST_TRACK_SECONDS = 3.0
_TRACKER_REFERENCE_FPS = 30.0

# CPU-bound pipelines run at a few fps, so consecutive boxes of a walking
# object barely overlap; the Kalman prediction carries the motion once a track
# starts, and the floor only rejects near-zero-overlap mismatches.
_MINIMUM_IOU_THRESHOLD = 0.02


class ByteTrackDetectionTracker:
    """Attach ByteTrack ids without filtering or reordering detector output.

    Ids confirm on the first matched frame: CPU-bound pipelines run at a few
    fps, and the default two-frame warm-up would delay ids past the moment a
    walking object crosses a line.
    """

    def __init__(self, frame_rate: float) -> None:
        self._tracker = ByteTrackTracker(
            frame_rate=frame_rate,
            lost_track_buffer=int(_LOST_TRACK_SECONDS * _TRACKER_REFERENCE_FPS),
            minimum_consecutive_frames=1,
            minimum_iou_threshold=_MINIMUM_IOU_THRESHOLD,
        )

    def update(self, detections: sv.Detections) -> sv.Detections:
        tracked = self._tracker.update(
            sv.Detections(
                xyxy=detections.xyxy,
                confidence=detections.confidence,
                class_id=detections.class_id,
                data={_SOURCE_INDEX_KEY: np.arange(len(detections), dtype=np.int64)},
            )
        )

        tracker_ids = np.full(len(detections), -1, dtype=np.int64)
        if len(tracked):
            source_indices = np.asarray(
                _required(tracked.data.get(_SOURCE_INDEX_KEY), "source indices"),
                dtype=np.int64,
            )
            tracked_ids = np.asarray(_required(tracked.tracker_id, "tracker ids"), dtype=np.int64)

            if len(source_indices) != len(tracked_ids):
                raise RuntimeError("ByteTrack returned inconsistent source indices")

            if (source_indices < 0).any() or (source_indices >= len(detections)).any():
                raise RuntimeError("ByteTrack returned out-of-range source indices")

            if len(np.unique(source_indices)) != len(source_indices):
                raise RuntimeError("ByteTrack returned duplicated source indices")

            tracker_ids[source_indices] = tracked_ids

        return sv.Detections(
            xyxy=detections.xyxy,
            confidence=detections.confidence,
            class_id=detections.class_id,
            tracker_id=tracker_ids,
        )


def _required[Value](value: Value | None, name: str) -> Value:
    if value is None:
        raise RuntimeError(f"ByteTrack returned no {name}")

    return value
