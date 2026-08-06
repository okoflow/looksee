"""Public contracts and model-asset helpers shared by API and inference."""

from shared.contracts.channels import (
    Channel,
    camera_id_from_path_name,
    camera_path_name,
    last_frame_key,
)
from shared.contracts.commands import StartStream, StopStream, StreamCommand
from shared.contracts.events import (
    Detection,
    DetectionFrame,
    WorkerErrored,
    WorkerEvent,
    WorkerStarted,
    WorkerStopped,
)
from shared.contracts.values import ModelId, WorkflowConfig
from shared.model_assets import (
    MANIFEST_FILENAME,
    MODEL_FILENAME,
    EventKind,
    bundle_model_path,
    read_manifest,
)

__all__ = [
    "MANIFEST_FILENAME",
    "MODEL_FILENAME",
    "Channel",
    "Detection",
    "DetectionFrame",
    "EventKind",
    "ModelId",
    "StartStream",
    "StopStream",
    "StreamCommand",
    "WorkerErrored",
    "WorkerEvent",
    "WorkerStarted",
    "WorkerStopped",
    "WorkflowConfig",
    "bundle_model_path",
    "camera_id_from_path_name",
    "camera_path_name",
    "last_frame_key",
    "read_manifest",
]
