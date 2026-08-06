from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import quote

from inference.adapters.video.rtsp import RtspReader
from shared import camera_path_name

if TYPE_CHECKING:
    from uuid import UUID


@dataclass(frozen=True, slots=True)
class MediaMtxFrameSourceFactory:
    """Build RTSP readers for camera paths exposed by MediaMTX."""

    base_url: str
    media_user: str
    media_password: str
    transport: str

    def create(self, camera_id: UUID, target_fps: int) -> RtspReader:
        return RtspReader(
            rtsp_url=self._camera_url(camera_id),
            target_fps=target_fps,
            transport=self.transport,
            source_name=str(camera_id),
        )

    def _camera_url(self, camera_id: UUID) -> str:
        base = self.base_url
        if self.media_password:
            user = quote(self.media_user, safe="")
            password = quote(self.media_password, safe="")
            scheme, _, host = base.partition("://")
            base = f"{scheme}://{user}:{password}@{host}"

        return f"{base}/{camera_path_name(camera_id)}"
