from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    import onnxruntime as ort
    import supervision as sv


class UnsupportedModelError(ValueError):
    """No registered adapter understands an ONNX model contract."""


@dataclass(frozen=True, slots=True)
class OnnxTensorSpec:
    name: str
    dtype: str
    shape: tuple[object, ...]

    @property
    def rank(self) -> int:
        return len(self.shape)


@dataclass(frozen=True, slots=True)
class OnnxSignature:
    inputs: tuple[OnnxTensorSpec, ...]
    outputs: tuple[OnnxTensorSpec, ...]

    @classmethod
    def from_session(cls, session: ort.InferenceSession) -> OnnxSignature:
        return cls(
            inputs=tuple(
                OnnxTensorSpec(item.name, item.type, tuple(item.shape))
                for item in session.get_inputs()
            ),
            outputs=tuple(
                OnnxTensorSpec(item.name, item.type, tuple(item.shape))
                for item in session.get_outputs()
            ),
        )

    @property
    def input_names(self) -> frozenset[str]:
        return frozenset(item.name for item in self.inputs)

    @property
    def output_names(self) -> frozenset[str]:
        return frozenset(item.name for item in self.outputs)

    def input(self, name: str) -> OnnxTensorSpec:
        return next(item for item in self.inputs if item.name == name)

    def output(self, name: str) -> OnnxTensorSpec:
        return next(item for item in self.outputs if item.name == name)

    def describe(self) -> str:
        def describe_tensor(item: OnnxTensorSpec) -> str:
            return f"{item.name}:{item.dtype}{item.shape}"

        inputs = ", ".join(describe_tensor(item) for item in self.inputs)
        outputs = ", ".join(describe_tensor(item) for item in self.outputs)

        return f"inputs=[{inputs}] outputs=[{outputs}]"


class OnnxDetectionAdapter(ABC):
    """Convert one ONNX architecture contract to normalized detections."""

    def __init__(self, session: ort.InferenceSession, signature: OnnxSignature) -> None:
        self._session = session

    @classmethod
    @abstractmethod
    def supports(cls, signature: OnnxSignature) -> bool:
        raise NotImplementedError

    @abstractmethod
    def detect(self, frame: np.ndarray) -> sv.Detections:
        raise NotImplementedError


def tensor_matches(
    tensor: OnnxTensorSpec,
    *,
    dtype: str,
    rank: int,
    fixed_dimensions: dict[int, int] | None = None,
) -> bool:
    if tensor.dtype != dtype:
        return False

    if tensor.rank != rank:
        return False

    if fixed_dimensions is None:
        return True

    return all(tensor.shape[index] == size for index, size in fixed_dimensions.items())


def square_input_size(signature: OnnxSignature, input_name: str) -> int:
    spec = signature.input(input_name)
    height, width = spec.shape[-2:]

    if not isinstance(height, int) or not isinstance(width, int):
        raise UnsupportedModelError(
            f"input '{input_name}' must have static spatial dimensions; got {spec.shape}"
        )

    if height != width or height < 1:
        raise UnsupportedModelError(
            f"input '{input_name}' must be square with a positive size; got {spec.shape}"
        )

    return height
