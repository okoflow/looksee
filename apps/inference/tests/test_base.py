from dataclasses import FrozenInstanceError

import pytest

from inference.adapters.onnx.base import (
    OnnxSignature,
    OnnxTensorSpec,
    UnsupportedModelError,
    square_input_size,
    tensor_matches,
)

IMAGES = OnnxTensorSpec("images", "tensor(float)", (1, 3, 640, 640))
SCORES = OnnxTensorSpec("scores", "tensor(float)", (1, 300))


def test_rank_counts_shape_dimensions():
    assert IMAGES.rank == 4
    assert SCORES.rank == 2


def test_tensor_spec_is_immutable():
    with pytest.raises(FrozenInstanceError):
        IMAGES.name = "input"


def test_signature_from_session_copies_tensor_metadata(deploy_signature, make_session):
    session = make_session(deploy_signature)

    signature = OnnxSignature.from_session(session)

    assert signature == deploy_signature


def test_name_sets_cover_inputs_and_outputs(deploy_signature):
    assert deploy_signature.input_names == {"images", "orig_target_sizes"}
    assert deploy_signature.output_names == {"labels", "boxes", "scores"}


def test_tensors_are_looked_up_by_name(deploy_signature):
    assert deploy_signature.input("orig_target_sizes").dtype == "tensor(int64)"
    assert deploy_signature.output("boxes").shape == (1, 300, 4)


def test_describe_lists_every_tensor():
    signature = OnnxSignature(inputs=(IMAGES,), outputs=(SCORES,))

    description = signature.describe()

    assert description == (
        "inputs=[images:tensor(float)(1, 3, 640, 640)] outputs=[scores:tensor(float)(1, 300)]"
    )


def test_tensor_matches_requires_dtype_and_rank():
    assert tensor_matches(IMAGES, dtype="tensor(float)", rank=4)
    assert not tensor_matches(IMAGES, dtype="tensor(int64)", rank=4)
    assert not tensor_matches(IMAGES, dtype="tensor(float)", rank=3)


def test_tensor_matches_checks_fixed_dimensions_by_index():
    assert tensor_matches(IMAGES, dtype="tensor(float)", rank=4, fixed_dimensions={1: 3, -1: 640})
    assert not tensor_matches(IMAGES, dtype="tensor(float)", rank=4, fixed_dimensions={1: 1})


def test_tensor_matches_treats_dynamic_dimension_as_mismatch():
    dynamic = OnnxTensorSpec("images", "tensor(float)", ("N", 3, "H", "W"))

    assert not tensor_matches(dynamic, dtype="tensor(float)", rank=4, fixed_dimensions={-1: 640})
    assert tensor_matches(dynamic, dtype="tensor(float)", rank=4, fixed_dimensions={1: 3})


def test_square_input_size_reads_static_spatial_size():
    signature = OnnxSignature(inputs=(IMAGES,), outputs=())

    assert square_input_size(signature, "images") == 640


@pytest.mark.parametrize("shape", [("N", 3, "H", "W"), (1, 3, None, None), (1, 3, 640, "W")])
def test_square_input_size_rejects_dynamic_spatial_dimensions(shape):
    signature = OnnxSignature(
        inputs=(OnnxTensorSpec("images", "tensor(float)", shape),), outputs=()
    )

    with pytest.raises(UnsupportedModelError, match="static spatial dimensions"):
        square_input_size(signature, "images")


@pytest.mark.parametrize("shape", [(1, 3, 640, 480), (1, 3, 0, 0)])
def test_square_input_size_rejects_non_square_or_empty_inputs(shape):
    signature = OnnxSignature(
        inputs=(OnnxTensorSpec("images", "tensor(float)", shape),), outputs=()
    )

    with pytest.raises(UnsupportedModelError, match="square with a positive size"):
        square_input_size(signature, "images")


def test_unsupported_model_error_is_a_value_error():
    assert issubclass(UnsupportedModelError, ValueError)
