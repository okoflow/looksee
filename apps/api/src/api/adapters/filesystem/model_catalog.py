"""Discover deployable inference models from the shared runtime asset directory."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from threading import RLock
from typing import TYPE_CHECKING

from pydantic import TypeAdapter

from api.config import settings
from api.domain.events import EVENT_KIND_DETECTED_SUFFIX
from api.domain.models import ModelClassDescriptor, ModelDescriptor
from shared import (
    MANIFEST_FILENAME,
    MODEL_FILENAME,
    EventKind,
    ModelId,
    bundle_model_path,
    read_manifest,
)

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

_model_id_adapter = TypeAdapter(ModelId)
_event_kind_adapter = TypeAdapter(EventKind)
_EVENT_SEPARATOR = re.compile(r"[^A-Z0-9]+")


@dataclass(frozen=True, slots=True)
class _CachedModel:
    fingerprint: tuple[tuple[int, int], ...]
    model: ModelDescriptor


def event_kind_for_label(label: str) -> str | None:
    """Convert an arbitrary detector label into a stable semantic event identifier."""
    normalized = _EVENT_SEPARATOR.sub("_", label.upper()).strip("_")
    if not normalized:
        logger.warning("label %r yields no event: normalizes to an empty identifier", label)
        return None

    if not normalized[0].isalpha():
        normalized = f"CLASS_{normalized}"

    kind = (
        normalized
        if normalized.endswith(EVENT_KIND_DETECTED_SUFFIX)
        else f"{normalized}{EVENT_KIND_DETECTED_SUFFIX}"
    )
    try:
        return _event_kind_adapter.validate_python(kind)
    except ValueError:
        logger.warning(
            "label %r yields no event: derived kind %r is not a valid EventKind", label, kind
        )
        return None


def _fallback_name(model_id: str) -> str:
    return model_id.replace("-", " ").replace("_", " ").title()


class ModelCatalog:
    """Discover new model ids while treating every cached model bundle as immutable."""

    def __init__(self, models_dir: Path) -> None:
        self._models_dir = models_dir
        self._cache: dict[str, _CachedModel] = {}
        self._warned_asset_changes: set[str] = set()
        self._lock = RLock()

    def list(self) -> tuple[ModelDescriptor, ...]:
        if self._models_dir.is_dir():
            for model_id in sorted(
                path.parent.name for path in self._models_dir.glob(f"*/{MODEL_FILENAME}")
            ):
                self.get(model_id)

        with self._lock:
            self._warn_about_changed_assets()

            return tuple(self._cache[model_id].model for model_id in sorted(self._cache))

    def get(self, model_id: str) -> ModelDescriptor | None:
        try:
            validated_id = _model_id_adapter.validate_python(model_id)
        except ValueError:
            return None

        with self._lock:
            cached = self._cache.get(validated_id)
            if cached is not None:
                return cached.model

            model_path = bundle_model_path(self._models_dir, validated_id)
            if not model_path.is_file():
                return None

            try:
                fingerprint = self._fingerprint(model_path)
                model = self._load(validated_id, model_path)
                self._cache[validated_id] = _CachedModel(fingerprint, model)

                return model
            except (OSError, ValueError) as exc:
                logger.warning("invalid model asset path=%s reason=%s", model_path, exc)

                return None

    def _warn_about_changed_assets(self) -> None:
        for model_id, cached in self._cache.items():
            if model_id in self._warned_asset_changes:
                continue

            model_path = bundle_model_path(self._models_dir, model_id)
            try:
                fingerprint = self._fingerprint(model_path)
            except OSError as exc:
                logger.warning(
                    "cannot verify immutable model asset model=%s reason=%s; keeping cached model",
                    model_id,
                    exc,
                )
                self._warned_asset_changes.add(model_id)
                continue

            if fingerprint != cached.fingerprint:
                logger.warning(
                    "model asset changed after discovery model=%s; keeping cached model",
                    model_id,
                )
                self._warned_asset_changes.add(model_id)

    @staticmethod
    def _fingerprint(model_path: Path) -> tuple[tuple[int, int], ...]:
        paths = (model_path, model_path.with_name(MANIFEST_FILENAME))
        fingerprint: list[tuple[int, int]] = []
        for path in paths:
            try:
                stat = path.stat()
            except FileNotFoundError:
                fingerprint.append((0, 0))
                continue
            fingerprint.append((stat.st_mtime_ns, stat.st_size))

        return tuple(fingerprint)

    @staticmethod
    def _load(model_id: str, model_path: Path) -> ModelDescriptor:
        if not model_path.with_name(MANIFEST_FILENAME).is_file():
            raise ValueError(f"missing {MANIFEST_FILENAME}")

        manifest = read_manifest(model_path.parent)

        classes = tuple(
            ModelClassDescriptor(
                class_id=class_id,
                label=label,
                event_kind=manifest.events.get(label, event_kind_for_label(label)),
            )
            for class_id, label in manifest.labels.items()
        )
        name = manifest.name if manifest.name is not None else _fallback_name(model_id)

        return ModelDescriptor(
            id=model_id,
            name=name,
            classes=classes,
            recommended_confidence_threshold=manifest.recommended_confidence_threshold,
        )


model_catalog = ModelCatalog(settings.models_dir)
