"""Model-output decoding shared by ONNX architecture adapters."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import supervision as sv

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from inference.adapters.onnx.preprocessing import LetterboxTransform

logger = logging.getLogger(__name__)


def stable_sigmoid(logits: NDArray[np.floating]) -> NDArray[np.floating]:
    return 1.0 / (1.0 + np.exp(-np.clip(logits, -80.0, 80.0)))


def to_detections(
    boxes_xyxy: NDArray[np.floating],
    confidence: NDArray[np.floating],
    class_ids: NDArray[np.integer],
) -> sv.Detections:
    """Normalize raw model rows into Detections, dropping out-of-contract rows loudly."""
    xyxy = np.asarray(boxes_xyxy, dtype=np.float32)
    scores = np.asarray(confidence, dtype=np.float32)
    labels = np.asarray(class_ids, dtype=np.int64)

    if xyxy.size == 0 and scores.size == 0 and labels.size == 0:
        return sv.Detections.empty()

    if xyxy.ndim != 2 or xyxy.shape[1] != 4:
        raise ValueError(f"boxes must have shape (N, 4); got {xyxy.shape}")

    if scores.shape != (len(xyxy),) or labels.shape != (len(xyxy),):
        raise ValueError(
            f"misaligned model outputs: boxes={xyxy.shape} scores={scores.shape} "
            f"class_ids={labels.shape}"
        )

    rows_by_rule = {
        "non_finite_box": np.isfinite(xyxy).all(axis=1),
        "non_finite_score": np.isfinite(scores),
        "score_outside_unit_range": (scores >= 0.0) & (scores <= 1.0),
        "negative_class_id": labels >= 0,
        "degenerate_box": (xyxy[:, 2] > xyxy[:, 0]) & (xyxy[:, 3] > xyxy[:, 1]),
    }
    valid = np.logical_and.reduce(list(rows_by_rule.values()))

    dropped = len(xyxy) - int(valid.sum())
    if dropped:
        counts = {name: int((~keep).sum()) for name, keep in rows_by_rule.items() if not keep.all()}
        logger.warning("dropped %d/%d out-of-contract detections: %s", dropped, len(xyxy), counts)

    return sv.Detections(xyxy=xyxy[valid], confidence=scores[valid], class_id=labels[valid])


def clip_boxes(
    xyxy: NDArray[np.float32],
    frame_width: int,
    frame_height: int,
) -> NDArray[np.float32]:
    xyxy[:, 0::2] = xyxy[:, 0::2].clip(0, frame_width)
    xyxy[:, 1::2] = xyxy[:, 1::2].clip(0, frame_height)

    return xyxy


def unletterbox_boxes(
    boxes_xyxy: NDArray[np.floating],
    transform: LetterboxTransform,
    frame_width: int,
    frame_height: int,
) -> NDArray[np.float32]:
    """Map letterboxed-canvas XYXY boxes back onto original frame pixels."""
    xyxy = np.asarray(boxes_xyxy, dtype=np.float32).copy()
    xyxy[:, 0::2] = (xyxy[:, 0::2] - transform.pad_x) / transform.scale
    xyxy[:, 1::2] = (xyxy[:, 1::2] - transform.pad_y) / transform.scale

    return clip_boxes(xyxy, frame_width, frame_height)


def cxcywh_to_xyxy_pixels(
    boxes_cxcywh: NDArray[np.floating],
    frame_width: int,
    frame_height: int,
) -> NDArray[np.float32]:
    """Denormalize CXCYWH boxes into clipped pixel XYXY coordinates."""
    center_x, center_y, width, height = np.asarray(boxes_cxcywh, dtype=np.float32).T
    xyxy = np.column_stack(
        [
            (center_x - width / 2) * frame_width,
            (center_y - height / 2) * frame_height,
            (center_x + width / 2) * frame_width,
            (center_y + height / 2) * frame_height,
        ]
    ).astype(np.float32)

    return clip_boxes(xyxy, frame_width, frame_height)
