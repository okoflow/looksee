from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

import numpy as np

from inference.adapters.onnx.base import (
    OnnxDetectionAdapter,
    OnnxSignature,
    square_input_size,
    tensor_matches,
)
from inference.adapters.onnx.postprocessing import to_detections, unletterbox_boxes
from inference.adapters.onnx.preprocessing import letterbox, to_chw_tensor

if TYPE_CHECKING:
    import onnxruntime as ort
    import supervision as sv


class DfineDeployAdapter(OnnxDetectionAdapter):
    """D-FINE deploy export with letterboxed input and decoded XYXY outputs."""

    _INPUTS: ClassVar[frozenset[str]] = frozenset({"images", "orig_target_sizes"})
    _OUTPUTS: ClassVar[frozenset[str]] = frozenset({"labels", "boxes", "scores"})

    def __init__(self, session: ort.InferenceSession, signature: OnnxSignature) -> None:
        super().__init__(session, signature)
        self._input_size = square_input_size(signature, "images")

    @classmethod
    def supports(cls, signature: OnnxSignature) -> bool:
        if signature.input_names != cls._INPUTS or signature.output_names != cls._OUTPUTS:
            return False

        return all(
            (
                tensor_matches(
                    signature.input("images"),
                    dtype="tensor(float)",
                    rank=4,
                    fixed_dimensions={1: 3},
                ),
                tensor_matches(
                    signature.input("orig_target_sizes"),
                    dtype="tensor(int64)",
                    rank=2,
                    fixed_dimensions={-1: 2},
                ),
                tensor_matches(
                    signature.output("labels"),
                    dtype="tensor(int64)",
                    rank=2,
                ),
                tensor_matches(
                    signature.output("boxes"),
                    dtype="tensor(float)",
                    rank=3,
                    fixed_dimensions={-1: 4},
                ),
                tensor_matches(
                    signature.output("scores"),
                    dtype="tensor(float)",
                    rank=2,
                ),
            )
        )

    def detect(self, frame: np.ndarray) -> sv.Detections:
        frame_height, frame_width = frame.shape[:2]
        canvas, transform = letterbox(frame, self._input_size)

        labels, boxes, scores = self._session.run(
            ["labels", "boxes", "scores"],
            {
                "images": to_chw_tensor(canvas),
                "orig_target_sizes": np.array(
                    [[self._input_size, self._input_size]],
                    dtype=np.int64,
                ),
            },
        )

        xyxy = unletterbox_boxes(boxes[0], transform, frame_width, frame_height)

        return to_detections(xyxy, scores[0], labels[0])
