"""Stable domain values shared by workflow policy and persistence mappings."""

from enum import StrEnum


class AlertSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class CameraSource(StrEnum):
    """How MediaMTX ingests a camera. Pull types proxy an upstream URL; `webrtc`
    is publisher-mode — a browser or device pushes the stream in via WHIP;
    `whep` pulls a remote WebRTC/WHEP endpoint; `file` loops a video file from
    the mounted media directory as if it were a live stream.
    """

    RTSP = "rtsp"
    RTMP = "rtmp"
    SRT = "srt"
    WEBRTC = "webrtc"
    WHEP = "whep"
    FILE = "file"


class CameraStatus(StrEnum):
    PENDING = "pending"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"
