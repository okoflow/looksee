"""Model bundle manifest shared by services that consume local model directories."""

from pathlib import Path
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

ClassId = Annotated[int, Field(ge=0)]
ClassLabel = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=128)]
EventKind = Annotated[str, Field(pattern=r"^[A-Z][A-Z0-9_]*$", max_length=64)]

MODEL_FILENAME = "model.onnx"
MANIFEST_FILENAME = "manifest.json"


def bundle_model_path(models_dir: Path, model_id: str) -> Path:
    """Path of the ONNX weights inside a model bundle directory."""
    return models_dir / model_id / MODEL_FILENAME


def read_manifest(bundle_dir: Path) -> "ModelManifest":
    """Parse the manifest stored beside the weights in a bundle directory."""
    manifest_path = bundle_dir / MANIFEST_FILENAME

    return ModelManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))


def _index_label_array(value: object) -> object:
    """Accept a bare label list by treating its positions as class ids."""
    if isinstance(value, list):
        return dict(enumerate(value))

    return value


class ModelManifest(BaseModel):
    """Metadata stored as manifest.json beside model.onnx in a model bundle directory."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=128)
    labels: Annotated[dict[ClassId, ClassLabel], BeforeValidator(_index_label_array)]
    recommended_confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    events: dict[ClassLabel, EventKind | None] = Field(default_factory=dict)

    @model_validator(mode="after")
    def check_labels(self) -> Self:
        if not self.labels:
            raise ValueError("at least one class label is required")

        if sorted(self.labels) != list(range(len(self.labels))):
            raise ValueError("class ids must be contiguous and start at zero")

        if len(set(self.labels.values())) != len(self.labels):
            raise ValueError("class labels must be unique")

        return self

    @model_validator(mode="after")
    def check_events_reference_known_labels(self) -> Self:
        unknown_labels = set(self.events).difference(self.labels.values())

        if unknown_labels:
            names = ", ".join(sorted(unknown_labels))
            raise ValueError(f"events map unknown labels: {names}")

        return self

    @model_validator(mode="after")
    def sort_labels_by_class_id(self) -> Self:
        self.labels = dict(sorted(self.labels.items()))

        return self
