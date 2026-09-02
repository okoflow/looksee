from dataclasses import FrozenInstanceError

import numpy as np
import pytest

from inference.adapters.onnx.preprocessing import LetterboxTransform, letterbox, to_chw_tensor


def test_to_chw_tensor_moves_bgr_pixels_into_rgb_planes():
    frame = np.zeros((2, 3, 3), dtype=np.uint8)
    frame[0, 0] = (255, 0, 0)

    tensor = to_chw_tensor(frame)

    assert tensor.shape == (1, 3, 2, 3)
    assert tensor.dtype == np.float32
    assert tensor[0, :, 0, 0].tolist() == [0.0, 0.0, 1.0]


def test_to_chw_tensor_scales_to_unit_range_contiguously():
    frame = np.full((4, 4, 3), 51, dtype=np.uint8)

    tensor = to_chw_tensor(frame)

    assert np.allclose(tensor, 0.2)
    assert tensor.flags["C_CONTIGUOUS"]


def test_letterbox_scales_wide_frame_and_pads_vertically():
    frame = np.full((480, 640, 3), 200, dtype=np.uint8)

    canvas, transform = letterbox(frame, 320)

    assert canvas.shape == (320, 320, 3)
    assert canvas.dtype == np.uint8
    assert transform == LetterboxTransform(scale=0.5, pad_x=0, pad_y=40)
    assert (canvas[:40] == 0).all()
    assert (canvas[40:280] == 200).all()
    assert (canvas[280:] == 0).all()


def test_letterbox_scales_tall_frame_and_pads_horizontally():
    frame = np.full((300, 100, 3), 9, dtype=np.uint8)

    canvas, transform = letterbox(frame, 150)

    assert transform == LetterboxTransform(scale=0.5, pad_x=50, pad_y=0)
    assert (canvas[:, :50] == 0).all()
    assert (canvas[:, 50:100] == 9).all()
    assert (canvas[:, 100:] == 0).all()


def test_letterbox_upscales_small_square_frame_without_padding():
    frame = np.full((10, 10, 3), 3, dtype=np.uint8)

    canvas, transform = letterbox(frame, 40)

    assert transform == LetterboxTransform(scale=4.0, pad_x=0, pad_y=0)
    assert (canvas == 3).all()


def test_letterbox_keeps_at_least_one_pixel_row_for_extreme_aspect():
    frame = np.full((1, 1000, 3), 5, dtype=np.uint8)

    canvas, transform = letterbox(frame, 100)

    assert transform == LetterboxTransform(scale=0.1, pad_x=0, pad_y=49)
    assert (canvas[49] == 5).all()


def test_letterbox_transform_is_immutable():
    transform = LetterboxTransform(scale=1.0, pad_x=0, pad_y=0)

    with pytest.raises(FrozenInstanceError):
        transform.scale = 2.0
