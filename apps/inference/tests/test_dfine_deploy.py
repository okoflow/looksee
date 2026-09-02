import numpy as np
import pytest

from inference.adapters.onnx.base import OnnxSignature, OnnxTensorSpec, UnsupportedModelError
from inference.adapters.onnx.models.dfine_deploy import DfineDeployAdapter

FRAME = np.full((16, 32, 3), 255, dtype=np.uint8)


def empty_outputs() -> dict[str, np.ndarray]:
    return {
        "labels": np.zeros((1, 0), dtype=np.int64),
        "boxes": np.zeros((1, 0, 4), dtype=np.float32),
        "scores": np.zeros((1, 0), dtype=np.float32),
    }


def test_supports_decoded_dfine_contract(deploy_signature):
    assert DfineDeployAdapter.supports(deploy_signature)


def test_rejects_raw_dfine_contract(raw_signature):
    assert not DfineDeployAdapter.supports(raw_signature)


def test_supports_dynamic_batch_and_query_dimensions():
    signature = OnnxSignature(
        inputs=(
            OnnxTensorSpec("images", "tensor(float)", ("N", 3, 640, 640)),
            OnnxTensorSpec("orig_target_sizes", "tensor(int64)", ("N", 2)),
        ),
        outputs=(
            OnnxTensorSpec("labels", "tensor(int64)", ("N", "Q")),
            OnnxTensorSpec("boxes", "tensor(float)", ("N", "Q", 4)),
            OnnxTensorSpec("scores", "tensor(float)", ("N", "Q")),
        ),
    )

    assert DfineDeployAdapter.supports(signature)


def test_rejects_renamed_image_input(deploy_signature):
    renamed = OnnxTensorSpec("input", "tensor(float)", (1, 3, 32, 32))
    signature = OnnxSignature(
        inputs=(renamed, deploy_signature.inputs[1]),
        outputs=deploy_signature.outputs,
    )

    assert not DfineDeployAdapter.supports(signature)


def test_rejects_extra_output(deploy_signature):
    masks = OnnxTensorSpec("masks", "tensor(float)", (1, 300, 32, 32))
    signature = OnnxSignature(
        inputs=deploy_signature.inputs,
        outputs=(*deploy_signature.outputs, masks),
    )

    assert not DfineDeployAdapter.supports(signature)


@pytest.mark.parametrize(
    "spec",
    [
        OnnxTensorSpec("images", "tensor(uint8)", (1, 3, 32, 32)),
        OnnxTensorSpec("images", "tensor(float)", (1, 32, 32, 3)),
        OnnxTensorSpec("images", "tensor(float)", (3, 32, 32)),
        OnnxTensorSpec("orig_target_sizes", "tensor(float)", (1, 2)),
        OnnxTensorSpec("orig_target_sizes", "tensor(int64)", (1, 4)),
        OnnxTensorSpec("labels", "tensor(float)", (1, 300)),
        OnnxTensorSpec("labels", "tensor(int64)", (300,)),
        OnnxTensorSpec("boxes", "tensor(float)", (1, 300, 5)),
        OnnxTensorSpec("boxes", "tensor(float)", (300, 4)),
        OnnxTensorSpec("scores", "tensor(float)", (1, 300, 1)),
        OnnxTensorSpec("scores", "tensor(int64)", (1, 300)),
    ],
    ids=lambda spec: f"{spec.name}:{spec.dtype}{spec.shape}",
)
def test_rejects_tensor_outside_contract(deploy_signature, with_tensor, spec):
    signature = with_tensor(deploy_signature, spec)

    assert not DfineDeployAdapter.supports(signature)


def test_requires_static_square_input(deploy_signature, with_tensor, make_session):
    dynamic = OnnxTensorSpec("images", "tensor(float)", (1, 3, "H", "W"))
    signature = with_tensor(deploy_signature, dynamic)

    with pytest.raises(UnsupportedModelError, match="static spatial dimensions"):
        DfineDeployAdapter(make_session(signature), signature)


def test_detect_feeds_letterboxed_canvas_and_its_size(deploy_signature, make_session):
    session = make_session(deploy_signature, empty_outputs())
    adapter = DfineDeployAdapter(session, deploy_signature)

    adapter.detect(FRAME)

    [feeds] = session.feeds
    assert feeds["images"].shape == (1, 3, 32, 32)
    assert feeds["images"].dtype == np.float32
    assert feeds["images"][0, :, 0, 0].tolist() == [0.0, 0.0, 0.0]
    assert feeds["images"][0, :, 16, 16].tolist() == [1.0, 1.0, 1.0]
    assert feeds["orig_target_sizes"].dtype == np.int64
    assert feeds["orig_target_sizes"].tolist() == [[32, 32]]


def test_detect_returns_empty_when_model_emits_nothing(deploy_signature, make_session):
    adapter = DfineDeployAdapter(make_session(deploy_signature, empty_outputs()), deploy_signature)

    detections = adapter.detect(FRAME)

    assert len(detections) == 0


def test_detect_maps_canvas_boxes_back_onto_frame(deploy_signature, make_session):
    results = {
        "labels": np.array([[2, 0]], dtype=np.int64),
        "boxes": np.array([[[0, 8, 16, 24], [16, 12, 32, 20]]], dtype=np.float32),
        "scores": np.array([[0.9, 0.4]], dtype=np.float32),
    }
    adapter = DfineDeployAdapter(make_session(deploy_signature, results), deploy_signature)

    detections = adapter.detect(FRAME)

    assert detections.xyxy.tolist() == [[0, 0, 16, 16], [16, 4, 32, 12]]
    assert detections.class_id.tolist() == [2, 0]
    assert np.allclose(detections.confidence, [0.9, 0.4])


def test_detect_drops_rows_outside_the_contract(deploy_signature, make_session):
    results = {
        "labels": np.array([[1, 1]], dtype=np.int64),
        "boxes": np.array([[[0, 8, 16, 24], [16, 12, 16, 20]]], dtype=np.float32),
        "scores": np.array([[0.9, 0.9]], dtype=np.float32),
    }
    adapter = DfineDeployAdapter(make_session(deploy_signature, results), deploy_signature)

    detections = adapter.detect(FRAME)

    assert detections.xyxy.tolist() == [[0, 0, 16, 16]]
