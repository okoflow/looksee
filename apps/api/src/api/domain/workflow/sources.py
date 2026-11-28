"""Camera source node payload and its runnable refinements."""

from typing import Annotated, Literal

from pydantic import AnyUrl, Field, StringConstraints, UrlConstraints

from api.domain.enums import CameraSource
from api.domain.workflow.base import WorkflowModel

RtspSourceUrl = Annotated[AnyUrl, UrlConstraints(allowed_schemes=["rtsp", "rtsps"])]
RtmpSourceUrl = Annotated[AnyUrl, UrlConstraints(allowed_schemes=["rtmp", "rtmps"])]
SrtSourceUrl = Annotated[AnyUrl, UrlConstraints(allowed_schemes=["srt"])]
WhepSourceUrl = Annotated[
    AnyUrl, UrlConstraints(allowed_schemes=["http", "https", "whep", "wheps"])
]

# Asset object key, also reused for cached file names. The pattern is deliberately
# conservative: it ends up inside a shell command executed by MediaMTX, so no
# spaces, no dotfiles, no `..` segments, no shell metacharacters.
MEDIA_FILE_PATH_PATTERN = r"^[A-Za-z0-9][A-Za-z0-9._-]*(?:/[A-Za-z0-9][A-Za-z0-9._-]*)*$"

MediaFilePath = Annotated[
    str,
    StringConstraints(min_length=1, max_length=1024, pattern=MEDIA_FILE_PATH_PATTERN),
]


DraftSourceUrl = Annotated[str, Field(max_length=2048)]


class _CameraSourceFields(WorkflowModel):
    kind: Literal["camera_source"] = "camera_source"
    name: str = Field(default="Camera", min_length=1, max_length=128)


class CameraSourceData(_CameraSourceFields):
    source_type: CameraSource = CameraSource.RTSP
    url: DraftSourceUrl = ""


class RunnableRtspSource(_CameraSourceFields):
    source_type: Literal[CameraSource.RTSP]
    url: RtspSourceUrl


class RunnableRtmpSource(_CameraSourceFields):
    source_type: Literal[CameraSource.RTMP]
    url: RtmpSourceUrl


class RunnableSrtSource(_CameraSourceFields):
    source_type: Literal[CameraSource.SRT]
    url: SrtSourceUrl


class RunnableWebrtcSource(_CameraSourceFields):
    """Publisher-mode ingest: the stream is pushed in via WHIP, so no URL is required."""

    source_type: Literal[CameraSource.WEBRTC]
    url: DraftSourceUrl = ""


class RunnableWhepSource(_CameraSourceFields):
    """Pull-mode WebRTC: MediaMTX reads a remote WHEP endpoint."""

    source_type: Literal[CameraSource.WHEP]
    url: WhepSourceUrl


class RunnableFileSource(_CameraSourceFields):
    """An asset-store object key; the file is cached locally and looped as a live stream."""

    source_type: Literal[CameraSource.FILE]
    url: MediaFilePath


RunnableCameraSourceData = Annotated[
    RunnableRtspSource
    | RunnableRtmpSource
    | RunnableSrtSource
    | RunnableWebrtcSource
    | RunnableWhepSource
    | RunnableFileSource,
    Field(discriminator="source_type"),
]
