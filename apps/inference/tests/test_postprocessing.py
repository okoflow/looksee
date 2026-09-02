import logging

import numpy as np
import pytest

from inference.adapters.onnx.postprocessing import (
    clip_boxes,
    cxcywh_to_xyxy_pixels,
    stable_sigmoid,
    to_detections,
    unletterbox_boxes,
)
from inference.adapters.onnx.preprocessing import LetterboxTransform


def test_stable_sigmoid_matches_logistic_function():
    logits = np.array([-2.0, 0.0, 2.0])

    scores = stable_sigmoid(logits)

    assert np.allclose(scores, 1.0 / (1.0 + np.exp(-logits)))


def test_stable_sigmoid_saturates_extreme_logits_without_overflow():
    scores = stable_sigmoid(np.array([-1000.0, 1000.0]))

    assert np.allclose(scores, [0.0, 1.0])


def test_to_detections_normalizes_dtypes():
    detections = to_detections([[0, 0, 10, 10], [5, 5, 20, 30]], [0.5, 0.9], [1, 2])

    assert len(detections) == 2
    assert detections.xyxy.dtype == np.float32
    assert detections.confidence.dtype == np.float32
    assert detections.class_id.dtype == np.int64


def test_to_detections_returns_empty_result_with_all_fields_for_no_rows():
    detections = to_detections(np.zeros((0, 4)), np.zeros(0), np.zeros(0, dtype=np.int64))

    assert len(detections) == 0
    assert detections.confidence is not None
    assert detections.class_id is not None


@pytest.mark.parametrize(
    ("boxes", "confidence", "class_ids", "rule"),
    [
        ([[0, 0, np.nan, 10]], [0.5], [0], "non_finite_box"),
        ([[0, 0, 10, 10]], [np.inf], [0], "non_finite_score"),
        ([[0, 0, 10, 10]], [1.5], [0], "score_outside_unit_range"),
        ([[0, 0, 10, 10]], [-0.1], [0], "score_outside_unit_range"),
        ([[0, 0, 10, 10]], [0.5], [-1], "negative_class_id"),
        ([[10, 0, 10, 10]], [0.5], [0], "degenerate_box"),
        ([[0, 10, 10, 5]], [0.5], [0], "degenerate_box"),
    ],
)
def test_to_detections_drops_out_of_contract_rows_and_names_the_rule(
    boxes, confidence, class_ids, rule, caplog
):
    with caplog.at_level(logging.WARNING):
        detections = to_detections(boxes, confidence, class_ids)

    assert len(detections) == 0
    assert f"'{rule}': 1" in caplog.text


def test_to_detections_keeps_valid_rows_in_order():
    boxes = [[0, 0, 10, 10], [5, 5, 5, 20], [1, 1, 2, 2]]

    detections = to_detections(boxes, [0.5, 0.6, 0.7], [0, 1, 2])

    assert detections.xyxy.tolist() == [[0, 0, 10, 10], [1, 1, 2, 2]]
    assert detections.class_id.tolist() == [0, 2]


def test_to_detections_rejects_boxes_without_four_columns():
    with pytest.raises(ValueError, match=r"boxes must have shape \(N, 4\)"):
        to_detections([[0, 0, 10]], [0.5], [0])


def test_to_detections_rejects_misaligned_outputs():
    with pytest.raises(ValueError, match="misaligned model outputs"):
        to_detections([[0, 0, 10, 10]], [0.5, 0.6], [0])


def test_clip_boxes_clamps_to_frame_in_place():
    xyxy = np.array([[-5, -5, 120, 90]], dtype=np.float32)

    clipped = clip_boxes(xyxy, 100, 80)

    assert clipped is xyxy
    assert xyxy.tolist() == [[0, 0, 100, 80]]


def test_unletterbox_boxes_maps_canvas_pixels_back_onto_frame():
    transform = LetterboxTransform(scale=0.5, pad_x=0, pad_y=40)

    xyxy = unletterbox_boxes(np.array([[10, 50, 110, 250]]), transform, 640, 480)

    assert xyxy.dtype == np.float32
    assert xyxy.tolist() == [[20, 20, 220, 420]]


def test_unletterbox_boxes_clips_padding_overhang_without_touching_input():
    canvas_boxes = np.array([[-10, 0, 330, 320]], dtype=np.float32)
    transform = LetterboxTransform(scale=0.5, pad_x=0, pad_y=40)

    xyxy = unletterbox_boxes(canvas_boxes, transform, 640, 480)

    assert xyxy.tolist() == [[0, 0, 640, 480]]
    assert canvas_boxes.tolist() == [[-10, 0, 330, 320]]


def test_cxcywh_to_xyxy_pixels_denormalizes_centers_and_sizes():
    boxes = [[0.5, 0.5, 0.5, 0.5], [0.25, 0.25, 0.2, 0.2]]

    xyxy = cxcywh_to_xyxy_pixels(boxes, 200, 100)

    assert xyxy.dtype == np.float32
    assert np.allclose(xyxy, [[50, 25, 150, 75], [30, 15, 70, 35]])


def test_cxcywh_to_xyxy_pixels_clips_boxes_crossing_the_border():
    xyxy = cxcywh_to_xyxy_pixels([[0.0, 1.0, 0.5, 0.5]], 200, 100)

    assert xyxy.tolist() == [[0, 75, 50, 100]]
