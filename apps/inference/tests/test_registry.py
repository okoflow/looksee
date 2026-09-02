import re

import pytest

from inference.adapters.onnx import registry
from inference.adapters.onnx.base import OnnxSignature, OnnxTensorSpec, UnsupportedModelError
from inference.adapters.onnx.models.dfine_deploy import DfineDeployAdapter
from inference.adapters.onnx.models.dfine_raw import DfineRawAdapter
from inference.adapters.onnx.registry import build_adapter


def test_selects_deploy_adapter_for_decoded_outputs(deploy_signature, make_session):
    adapter = build_adapter(make_session(deploy_signature))

    assert isinstance(adapter, DfineDeployAdapter)


def test_selects_raw_adapter_for_logit_outputs(raw_signature, make_session):
    adapter = build_adapter(make_session(raw_signature))

    assert isinstance(adapter, DfineRawAdapter)


def test_rejects_signature_no_adapter_understands(make_session):
    signature = OnnxSignature(
        inputs=(OnnxTensorSpec("images", "tensor(float)", (1, 3, 640, 640)),),
        outputs=(OnnxTensorSpec("output0", "tensor(float)", (1, 84, 8400)),),
    )

    with pytest.raises(UnsupportedModelError, match=re.escape(signature.describe())):
        build_adapter(make_session(signature))


def test_rejects_matching_contract_with_dynamic_input_size(
    deploy_signature, with_tensor, make_session
):
    dynamic = OnnxTensorSpec("images", "tensor(float)", (1, 3, "H", "W"))
    signature = with_tensor(deploy_signature, dynamic)

    with pytest.raises(UnsupportedModelError, match="static spatial dimensions"):
        build_adapter(make_session(signature))


def test_rejects_signature_claimed_by_several_adapters(raw_signature, make_session, monkeypatch):
    class ShadowAdapter(DfineRawAdapter):
        """Second adapter claiming the raw contract."""

    monkeypatch.setattr(registry, "_ADAPTER_TYPES", (DfineRawAdapter, ShadowAdapter))

    with pytest.raises(
        UnsupportedModelError,
        match="ambiguous ONNX signature matched adapters: DfineRawAdapter, ShadowAdapter",
    ):
        build_adapter(make_session(raw_signature))
