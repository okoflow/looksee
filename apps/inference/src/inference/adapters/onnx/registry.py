from __future__ import annotations

from typing import TYPE_CHECKING

from inference.adapters.onnx.base import (
    OnnxDetectionAdapter,
    OnnxSignature,
    UnsupportedModelError,
)
from inference.adapters.onnx.models.dfine_deploy import DfineDeployAdapter
from inference.adapters.onnx.models.dfine_raw import DfineRawAdapter

if TYPE_CHECKING:
    import onnxruntime as ort

_ADAPTER_TYPES: tuple[type[OnnxDetectionAdapter], ...] = (
    DfineDeployAdapter,
    DfineRawAdapter,
)


def build_adapter(session: ort.InferenceSession) -> OnnxDetectionAdapter:
    """Build the one architecture adapter matching an ONNX tensor contract."""
    signature = OnnxSignature.from_session(session)
    matches = [adapter_type for adapter_type in _ADAPTER_TYPES if adapter_type.supports(signature)]

    match matches:
        case [adapter_type]:
            return adapter_type(session, signature)
        case []:
            raise UnsupportedModelError(f"unsupported ONNX signature {signature.describe()}")
        case conflicting_types:
            names = ", ".join(sorted(adapter_type.__name__ for adapter_type in conflicting_types))
            raise UnsupportedModelError(f"ambiguous ONNX signature matched adapters: {names}")
