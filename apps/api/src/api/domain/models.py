"""Runtime model descriptors consumed by workflow validation and editing."""

from pydantic import BaseModel, ConfigDict, Field

from shared import EventKind, ModelId


class ModelClassDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    class_id: int = Field(ge=0)
    label: str = Field(min_length=1, max_length=128)
    event_kind: EventKind | None


class ModelDescriptor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: ModelId
    name: str = Field(min_length=1, max_length=128)
    classes: tuple[ModelClassDescriptor, ...]
    recommended_confidence_threshold: float | None = Field(default=None, ge=0.0, le=1.0)

    def event_classes(self) -> tuple[ModelClassDescriptor, ...]:
        return tuple(
            model_class for model_class in self.classes if model_class.event_kind is not None
        )

    def events_by_label(self) -> dict[str, EventKind]:
        return {
            model_class.label: model_class.event_kind
            for model_class in self.classes
            if model_class.event_kind is not None
        }
