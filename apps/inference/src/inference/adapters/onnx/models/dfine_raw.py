from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import cv2
import numpy as np

from inference.adapters.onnx.base import (
    OnnxDetectionAdapter,
    OnnxSignature,
    square_input_size,
    tensor_matches,
)
from inference.adapters.onnx.postprocessing import (
    cxcywh_to_xyxy_pixels,
    stable_sigmoid,
    to_detections,
)
from inference.adapters.onnx.preprocessing import to_chw_tensor

if TYPE_CHECKING:
    import onnxruntime as ort
    import supervision as sv


class DfineRawAdapter(OnnxDetectionAdapter):
    """Legacy raw D-FINE export with sigmoid logits and normalized CXCYWH boxes.

    Decoding mirrors the official DFINEPostProcessor: top query-count (query, class)
    pairs over flattened sigmoid scores, so one query may yield several classes.
    """

    _OUTPUTS: ClassVar[frozenset[str]] = frozenset({"logits", "pred_boxes"})

    def __init__(self, session: ort.InferenceSession, signature: OnnxSignature) -> None:
        super().__init__(session, signature)
        self._input_name = signature.inputs[0].name
        self._input_size = square_input_size(signature, self._input_name)

    @classmethod
    def supports(cls, signature: OnnxSignature) -> bool:
        if len(signature.inputs) != 1 or signature.output_names != cls._OUTPUTS:
            return False

        return all(
            (
                tensor_matches(
                    signature.inputs[0],
                    dtype="tensor(float)",
                    rank=4,
                    fixed_dimensions={1: 3},
                ),
                tensor_matches(
                    signature.output("logits"),
                    dtype="tensor(float)",
                    rank=3,
                ),
                tensor_matches(
                    signature.output("pred_boxes"),
                    dtype="tensor(float)",
                    rank=3,
                    fixed_dimensions={-1: 4},
                ),
            )
        )

    def detect(self, frame: np.ndarray) -> sv.Detections:
        frame_height, frame_width = frame.shape[:2]
        resized = cv2.resize(frame, (self._input_size, self._input_size))

        logits, boxes = self._session.run(
            ["logits", "pred_boxes"],
            {self._input_name: to_chw_tensor(resized)},
        )

        scores = stable_sigmoid(logits[0])
        num_queries, num_classes = scores.shape
        flat_scores = scores.reshape(-1)
        top_flat_indices = np.argsort(flat_scores)[-num_queries:][::-1]

        confidence = flat_scores[top_flat_indices].astype(np.float32)
        class_ids = (top_flat_indices % num_classes).astype(np.int64)
        query_indices = top_flat_indices // num_classes
        xyxy = cxcywh_to_xyxy_pixels(boxes[0][query_indices], frame_width, frame_height)

        return to_detections(xyxy, confidence, class_ids)
