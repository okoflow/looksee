"""Load, validate and cache architecture-independent ONNX detectors."""

from __future__ import annotations

import asyncio
import logging
import math
import os
from pathlib import Path
from typing import TYPE_CHECKING

import onnxruntime as ort

from inference.adapters.onnx.registry import build_adapter
from shared import MANIFEST_FILENAME, bundle_model_path, read_manifest

if TYPE_CHECKING:
    import numpy as np
    import supervision as sv

logger = logging.getLogger(__name__)

_PROVIDER_PRIORITY = (
    "CUDAExecutionProvider",
    "CoreMLExecutionProvider",
    "CPUExecutionProvider",
)

_CGROUP_CPU_MAX_PATH = Path("/sys/fs/cgroup/cpu.max")


def _resolve_providers() -> list[str]:
    available = ort.get_available_providers()

    return [name for name in _PROVIDER_PRIORITY if name in available]


def _session_options() -> ort.SessionOptions:
    """Cap the intra-op pool at the cgroup cpu quota; otherwise trust ORT.

    ONNX Runtime sizes its thread pool by host cores and ignores cgroup
    limits, so a quota-capped container oversubscribes its quota and stalls
    on scheduler churn. Outside that case its own core policy wins: forcing
    a count on Apple Silicon spills onto efficiency cores and slows runs.
    """
    options = ort.SessionOptions()

    quota = _cgroup_cpu_quota()
    if quota is not None and quota < (os.cpu_count() or 1):
        options.intra_op_num_threads = quota

    return options


def _cgroup_cpu_quota() -> int | None:
    try:
        cpu_max = _CGROUP_CPU_MAX_PATH.read_text()
    except OSError:
        return None

    quota_text, _, period_text = cpu_max.partition(" ")
    if quota_text == "max":
        return None

    try:
        quota = int(quota_text)
        period = int(period_text)
    except ValueError:
        logger.warning("skipping unparseable cgroup cpu.max: %r", cpu_max)

        return None

    if quota <= 0 or period <= 0:
        return None

    return math.ceil(quota / period)


class Detector:
    """One ONNX session plus a normalized architecture adapter and labels."""

    def __init__(self, model_path: Path, labels: dict[int, str]) -> None:
        options = _session_options()
        session = ort.InferenceSession(
            str(model_path),
            sess_options=options,
            providers=_resolve_providers(),
        )
        self._adapter = build_adapter(session)
        self._labels = labels

        logger.info(
            "model loaded name=%s adapter=%s labels=%d providers=%s intra_op_threads=%s",
            model_path.parent.name,
            type(self._adapter).__name__,
            len(labels),
            session.get_providers(),
            options.intra_op_num_threads or "auto",
        )

    def label_for(self, class_id: int) -> str:
        try:
            return self._labels[class_id]
        except KeyError as exc:
            raise ValueError(f"model returned unknown class id: {class_id}") from exc

    def detect(self, frame: np.ndarray) -> sv.Detections:
        return self._adapter.detect(frame)


class DetectorRegistry:
    """Load each immutable model id once and share its session across workers."""

    def __init__(self, models_dir: Path) -> None:
        self._models_dir = models_dir
        self._detectors: dict[str, Detector] = {}
        self._load_locks: dict[str, asyncio.Lock] = {}

    async def get(self, model_id: str) -> Detector:
        detector = self._detectors.get(model_id)
        if detector is not None:
            return detector

        lock = self._load_locks.setdefault(model_id, asyncio.Lock())
        async with lock:
            detector = self._detectors.get(model_id)
            if detector is None:
                detector = await asyncio.to_thread(self._load, model_id)
                self._detectors[model_id] = detector

            return detector

    def _load(self, model_id: str) -> Detector:
        model_path = bundle_model_path(self._models_dir, model_id)
        if not model_path.is_file():
            raise FileNotFoundError(f"model file not found: {model_path}")

        bundle_dir = model_path.parent
        manifest_path = bundle_dir / MANIFEST_FILENAME
        if not manifest_path.is_file():
            raise FileNotFoundError(f"model manifest not found: {manifest_path}")

        manifest = read_manifest(bundle_dir)

        return Detector(model_path, manifest.labels)
