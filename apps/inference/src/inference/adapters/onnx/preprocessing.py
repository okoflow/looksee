"""Frame-to-tensor conversion shared by ONNX architecture adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import cv2
import numpy as np

if TYPE_CHECKING:
    from numpy.typing import NDArray


def to_chw_tensor(bgr_frame: NDArray[np.uint8]) -> NDArray[np.float32]:
    """BGR HWC uint8 frame to a batched RGB CHW float32 tensor in [0, 1]."""
    rgb = cv2.cvtColor(bgr_frame, cv2.COLOR_BGR2RGB)
    channels_first = rgb.transpose(2, 0, 1).astype(np.float32) / 255.0

    return np.ascontiguousarray(channels_first[None])


@dataclass(frozen=True, slots=True)
class LetterboxTransform:
    scale: float
    pad_x: int
    pad_y: int


def letterbox(
    frame: NDArray[np.uint8],
    size: int,
) -> tuple[NDArray[np.uint8], LetterboxTransform]:
    """Resize keeping aspect ratio and pad onto a square canvas of the given size."""
    frame_height, frame_width = frame.shape[:2]
    scale = min(size / frame_width, size / frame_height)
    resized_width = max(1, round(frame_width * scale))
    resized_height = max(1, round(frame_height * scale))

    resized = cv2.resize(frame, (resized_width, resized_height))
    canvas = np.zeros((size, size, 3), dtype=np.uint8)
    pad_x = (size - resized_width) // 2
    pad_y = (size - resized_height) // 2
    canvas[pad_y : pad_y + resized_height, pad_x : pad_x + resized_width] = resized

    return canvas, LetterboxTransform(scale=scale, pad_x=pad_x, pad_y=pad_y)
