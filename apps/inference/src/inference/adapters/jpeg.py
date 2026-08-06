from __future__ import annotations

from typing import TYPE_CHECKING

import cv2

if TYPE_CHECKING:
    import numpy as np

_JPEG_QUALITY = 80


def encode_jpeg(frame: np.ndarray) -> bytes | None:
    ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, _JPEG_QUALITY])
    if not ok:
        return None

    return buffer.tobytes()
