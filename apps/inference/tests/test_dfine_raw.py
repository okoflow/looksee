import numpy as np
import pytest

from inference.adapters.onnx.base import OnnxSignature, OnnxTensorSpec, UnsupportedModelError
from inference.adapters.onnx.models.dfine_raw import DfineRawAdapter
from inference.adapters.onnx.postprocessing import stable_sigmoid

FRAME = np.zeros((100, 200, 3), dtype=np.uint8)


def single_query_outputs() -> dict[str, np.ndarray]:
    return {
        "logits": np.array([[[3.0, -3.0, -3.0]]], dtype=np.float32),
        "pred_boxes": np.array([[[0.5, 0.5, 0.5, 0.5]]], dtype=np.float32),
    }


def test_supports_raw_dfine_contract(raw_signature):
    assert DfineRawAdapter.supports(raw_signature)


def test_rejects_decoded_dfine_contract(deploy_signature):
    assert not DfineRawAdapter.supports(deploy_signature)


def test_accepts_any_single_input_name(raw_signature):
    signature = OnnxSignature(
        inputs=(OnnxTensorSpec("input", "tensor(float)", (1, 3, 32, 32)),),
        outputs=raw_signature.outputs,
    )

    assert DfineRawAdapter.supports(signature)


def test_supports_dynamic_batch_and_query_dimensions():
    signature = OnnxSignature(
        inputs=(OnnxTensorSpec("images", "tensor(float)", ("N", 3, 640, 640)),),
        outputs=(
            OnnxTensorSpec("logits", "tensor(float)", ("N", "Q", 80)),
            OnnxTensorSpec("pred_boxes", "tensor(float)", ("N", "Q", 4)),
        ),
    )

    assert DfineRawAdapter.supports(signature)


def test_rejects_second_input(raw_signature):
    sizes = OnnxTensorSpec("orig_target_sizes", "tensor(int64)", (1, 2))
    signature = OnnxSignature(inputs=(*raw_signature.inputs, sizes), outputs=raw_signature.outputs)

    assert not DfineRawAdapter.supports(signature)


def test_rejects_renamed_output(raw_signature):
    scores = OnnxTensorSpec("scores", "tensor(float)", (1, 300, 3))
    signature = OnnxSignature(
        inputs=raw_signature.inputs, outputs=(scores, raw_signature.outputs[1])
    )

    assert not DfineRawAdapter.supports(signature)


@pytest.mark.parametrize(
    "spec",
    [
        OnnxTensorSpec("images", "tensor(uint8)", (1, 3, 32, 32)),
        OnnxTensorSpec("images", "tensor(float)", (1, 32, 32, 3)),
        OnnxTensorSpec("images", "tensor(float)", (3, 32, 32)),
        OnnxTensorSpec("logits", "tensor(int64)", (1, 300, 3)),
        OnnxTensorSpec("logits", "tensor(float)", (1, 300)),
        OnnxTensorSpec("pred_boxes", "tensor(float)", (1, 300, 5)),
        OnnxTensorSpec("pred_boxes", "tensor(float)", (300, 4)),
    ],
    ids=lambda spec: f"{spec.name}:{spec.dtype}{spec.shape}",
)
def test_rejects_tensor_outside_contract(raw_signature, with_tensor, spec):
    signature = with_tensor(raw_signature, spec)

    assert not DfineRawAdapter.supports(signature)


def test_requires_static_square_input(raw_signature, with_tensor, make_session):
    dynamic = OnnxTensorSpec("images", "tensor(float)", ("N", 3, "H", "W"))
    signature = with_tensor(raw_signature, dynamic)

    with pytest.raises(UnsupportedModelError, match="static spatial dimensions"):
        DfineRawAdapter(make_session(signature), signature)


def test_detect_resizes_frame_to_the_model_input(raw_signature, make_session):
    session = make_session(raw_signature, single_query_outputs())
    adapter = DfineRawAdapter(session, raw_signature)

    adapter.detect(FRAME)

    [feeds] = session.feeds
    assert feeds["images"].shape == (1, 3, 32, 32)
    assert feeds["images"].dtype == np.float32


def test_detect_feeds_the_models_input_name(raw_signature, make_session):
    signature = OnnxSignature(
        inputs=(OnnxTensorSpec("input", "tensor(float)", (1, 3, 32, 32)),),
        outputs=raw_signature.outputs,
    )
    session = make_session(signature, single_query_outputs())
    adapter = DfineRawAdapter(session, signature)

    adapter.detect(FRAME)

    assert list(session.feeds[0]) == ["input"]


def test_detect_decodes_top_query_class_pairs_in_score_order(raw_signature, make_session):
    results = {
        "logits": np.array([[[-5.0, 4.0, -5.0], [5.0, -5.0, -5.0]]], dtype=np.float32),
        "pred_boxes": np.array([[[0.25, 0.25, 0.2, 0.2], [0.5, 0.5, 0.5, 0.5]]], dtype=np.float32),
    }
    adapter = DfineRawAdapter(make_session(raw_signature, results), raw_signature)

    detections = adapter.detect(FRAME)

    assert np.allclose(detections.xyxy, [[50, 25, 150, 75], [30, 15, 70, 35]])
    assert detections.class_id.tolist() == [0, 1]
    assert np.allclose(detections.confidence, stable_sigmoid(np.array([5.0, 4.0])))


def test_detect_lets_one_query_yield_several_classes(raw_signature, make_session):
    results = {
        "logits": np.array([[[5.0, 4.5, -5.0], [-5.0, -5.0, -5.0]]], dtype=np.float32),
        "pred_boxes": np.array([[[0.5, 0.5, 0.5, 0.5], [0.1, 0.1, 0.1, 0.1]]], dtype=np.float32),
    }
    adapter = DfineRawAdapter(make_session(raw_signature, results), raw_signature)

    detections = adapter.detect(FRAME)

    assert detections.class_id.tolist() == [0, 1]
    assert detections.xyxy.tolist() == [[50, 25, 150, 75], [50, 25, 150, 75]]


def test_detect_emits_one_row_per_query_without_thresholding(raw_signature, make_session):
    results = {
        "logits": np.full((1, 3, 3), -5.0, dtype=np.float32),
        "pred_boxes": np.full((1, 3, 4), 0.5, dtype=np.float32),
    }
    adapter = DfineRawAdapter(make_session(raw_signature, results), raw_signature)

    detections = adapter.detect(FRAME)

    assert len(detections) == 3
    assert (detections.confidence < 0.01).all()
