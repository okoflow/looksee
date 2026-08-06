from enum import StrEnum
from uuid import UUID


class Channel(StrEnum):
    STREAM_COMMANDS = "stream.commands"
    WORKER_EVENTS = "worker.events"
    DETECTION_FRAMES = "detection.frames"


def last_frame_key(camera_id: UUID) -> str:
    """Redis key where inference keeps the camera's most recent JPEG frame."""
    return f"frames.last.{camera_id}"


def camera_path_name(camera_id: UUID) -> str:
    """MediaMTX path name under which the camera's stream is published."""
    return str(camera_id)


def camera_id_from_path_name(path_name: str) -> UUID | None:
    """Camera id encoded in a MediaMTX path name; None for foreign paths."""
    try:
        return UUID(path_name)
    except ValueError:
        return None
