from types import SimpleNamespace
from uuid import uuid4

import numpy as np
import pytest

from inference.adapters.onnx.base import OnnxSignature, OnnxTensorSpec
from shared import StartStream, WorkflowConfig

INPUT_SIZE = 32


class FakeSession:
    """Stand-in for an onnxruntime session that replays canned outputs."""

    def __init__(
        self,
        signature: OnnxSignature,
        results: dict[str, np.ndarray] | None = None,
    ) -> None:
        self._signature = signature
        self.results = results or {}
        self.feeds: list[dict[str, np.ndarray]] = []

    def get_inputs(self) -> list[SimpleNamespace]:
        return [_node_arg(spec) for spec in self._signature.inputs]

    def get_outputs(self) -> list[SimpleNamespace]:
        return [_node_arg(spec) for spec in self._signature.outputs]

    def run(self, output_names: list[str], feeds: dict[str, np.ndarray]) -> list[np.ndarray]:
        self.feeds.append(feeds)

        return [self.results[name] for name in output_names]


def _node_arg(spec: OnnxTensorSpec) -> SimpleNamespace:
    return SimpleNamespace(name=spec.name, type=spec.dtype, shape=list(spec.shape))


@pytest.fixture
def deploy_signature() -> OnnxSignature:
    return OnnxSignature(
        inputs=(
            OnnxTensorSpec("images", "tensor(float)", (1, 3, INPUT_SIZE, INPUT_SIZE)),
            OnnxTensorSpec("orig_target_sizes", "tensor(int64)", (1, 2)),
        ),
        outputs=(
            OnnxTensorSpec("labels", "tensor(int64)", (1, 300)),
            OnnxTensorSpec("boxes", "tensor(float)", (1, 300, 4)),
            OnnxTensorSpec("scores", "tensor(float)", (1, 300)),
        ),
    )


@pytest.fixture
def raw_signature() -> OnnxSignature:
    return OnnxSignature(
        inputs=(OnnxTensorSpec("images", "tensor(float)", (1, 3, INPUT_SIZE, INPUT_SIZE)),),
        outputs=(
            OnnxTensorSpec("logits", "tensor(float)", (1, 300, 3)),
            OnnxTensorSpec("pred_boxes", "tensor(float)", (1, 300, 4)),
        ),
    )


@pytest.fixture
def make_session() -> type[FakeSession]:
    return FakeSession


@pytest.fixture
def with_tensor():
    def replace(signature: OnnxSignature, spec: OnnxTensorSpec) -> OnnxSignature:
        inputs = tuple(spec if item.name == spec.name else item for item in signature.inputs)
        outputs = tuple(spec if item.name == spec.name else item for item in signature.outputs)

        return OnnxSignature(inputs=inputs, outputs=outputs)

    return replace


@pytest.fixture
def make_start_command():
    def make(**overrides) -> StartStream:
        fields = {
            "camera_id": uuid4(),
            "workflow_id": uuid4(),
            "revision": 1,
            "run_id": uuid4(),
            "config": WorkflowConfig(model_id="dfine-m-ppe"),
        }
        fields.update(overrides)

        return StartStream(**fields)

    return make
