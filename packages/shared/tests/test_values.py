import pytest
from pydantic import TypeAdapter, ValidationError

from shared import ModelId, WorkflowConfig

MODEL_ID = TypeAdapter(ModelId)


def test_defaults_apply_when_only_model_id_is_given():
    config = WorkflowConfig(model_id="dfine-m-ppe")

    assert config.confidence_threshold == 0.5
    assert config.inference_fps == 1


def test_requires_model_id():
    with pytest.raises(ValidationError, match=r"model_id\s+Field required"):
        WorkflowConfig()


def test_rejects_unknown_fields():
    with pytest.raises(ValidationError, match="extra_forbidden"):
        WorkflowConfig(model_id="dfine-m-ppe", batch_size=4)


def test_is_immutable_after_validation():
    config = WorkflowConfig(model_id="dfine-m-ppe")

    with pytest.raises(ValidationError, match="frozen_instance"):
        config.confidence_threshold = 0.9


@pytest.mark.parametrize("confidence_threshold", [-0.1, 1.1])
def test_rejects_confidence_outside_unit_range(confidence_threshold):
    with pytest.raises(ValidationError, match="confidence_threshold"):
        WorkflowConfig(model_id="dfine-m-ppe", confidence_threshold=confidence_threshold)


@pytest.mark.parametrize("inference_fps", [0, 16])
def test_rejects_fps_outside_supported_range(inference_fps):
    with pytest.raises(ValidationError, match="inference_fps"):
        WorkflowConfig(model_id="dfine-m-ppe", inference_fps=inference_fps)


@pytest.mark.parametrize("model_id", ["dfine-m-ppe", "yolo_v8", "a", "0" * 64])
def test_model_id_accepts_slugs(model_id):
    assert MODEL_ID.validate_python(model_id) == model_id


@pytest.mark.parametrize("model_id", ["", "Dfine", "dfine m", "dfine/ppe", "a" * 65])
def test_model_id_rejects_non_slug_values(model_id):
    with pytest.raises(ValidationError):
        MODEL_ID.validate_python(model_id)


def test_round_trips_through_json():
    config = WorkflowConfig(model_id="dfine-m-ppe", confidence_threshold=0.3, inference_fps=5)

    restored = WorkflowConfig.model_validate_json(config.model_dump_json())

    assert restored == config
