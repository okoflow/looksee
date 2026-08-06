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


class CameraSourceData(WorkflowModel):
    kind: Literal["camera_source"] = "camera_source"
    name: str = Field(default="Camera", min_length=1, max_length=128)
    source_type: CameraSource = CameraSource.RTSP
    url: str = Field(default="", max_length=2048)


class RunnableRtspSource(CameraSourceData):
    source_type: Literal[CameraSource.RTSP]
    url: RtspSourceUrl


class RunnableRtmpSource(CameraSourceData):
    source_type: Literal[CameraSource.RTMP]
    url: RtmpSourceUrl


class RunnableSrtSource(CameraSourceData):
    source_type: Literal[CameraSource.SRT]
    url: SrtSourceUrl


class RunnableWebrtcSource(CameraSourceData):
    """Publisher-mode ingest: the stream is pushed in via WHIP, so no URL is required."""

    source_type: Literal[CameraSource.WEBRTC]


class RunnableWhepSource(CameraSourceData):
    """Pull-mode WebRTC: MediaMTX reads a remote WHEP endpoint."""

    source_type: Literal[CameraSource.WHEP]
    url: WhepSourceUrl


class RunnableFileSource(CameraSourceData):
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
