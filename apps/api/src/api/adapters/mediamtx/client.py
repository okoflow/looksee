"""Thin wrapper around the mediamtx control plane HTTP API.

Each camera_id maps to one mediamtx path. Pull cameras (rtsp/rtmp/srt) proxy
an upstream URL on demand — mediamtx infers the protocol from the URL scheme. A
`whep` camera pulls a remote WebRTC server via its WHEP endpoint. A `file`
camera loops an asset-store video, cached into the media volume by the api,
through an on-demand ffmpeg publisher inside the mediamtx container. A `webrtc` camera is
publisher-mode: a browser or device pushes the stream in via WHIP at
`{webrtc_url}/{camera_id}/whip`, so the path waits for a publisher and sets no
source. Either way inference reads `rtsp://mediamtx:8554/{camera_id}` and the
browser plays `{webrtc_url}/{camera_id}/whep`. Add/replace/delete are
idempotent so retries are safe.
"""

from __future__ import annotations

import logging
import posixpath
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit, urlunsplit

import httpx
from pydantic import TypeAdapter, ValidationError

from api.adapters.http.client import client
from api.config import settings
from api.domain.enums import CameraSource
from api.domain.workflow.sources import MediaFilePath
from shared import camera_path_name

if TYPE_CHECKING:
    from uuid import UUID

logger = logging.getLogger(__name__)

_PATH_TIMEOUT = 5.0
_API_BASE = settings.mediamtx_api_url.rstrip("/")

_media_file_path_adapter: TypeAdapter[MediaFilePath] = TypeAdapter(MediaFilePath)

_WHEP_SCHEMES = {"http": "whep", "https": "wheps", "whep": "whep", "wheps": "wheps"}

# Re-encode to H.264 so any input codec both feeds inference and plays back over
# WebRTC; `-re -stream_loop -1` paces the file at native speed and loops forever.
_FILE_PUBLISH_COMMAND = (
    "ffmpeg -hide_banner -loglevel warning -re -stream_loop -1 -i {input} "
    "-c:v libx264 -preset veryfast -tune zerolatency -pix_fmt yuv420p -g 60 -an "
    "-f rtsp -rtsp_transport tcp rtsp://localhost:8554/$MTX_PATH"
)


def _pull_source(source_type: CameraSource, source_url: str) -> str | None:
    """Resolve the mediamtx `source` value, or None when the URL cannot be one."""
    if source_type != CameraSource.WHEP:
        return source_url

    parsed = urlsplit(source_url)
    scheme = _WHEP_SCHEMES.get(parsed.scheme)
    if scheme is None:
        logger.warning("unsupported whep source scheme %r; leaving path sourceless", parsed.scheme)

        return None

    return urlunsplit(parsed._replace(scheme=scheme))


def _file_path_body(source_url: str) -> dict[str, Any]:
    """On-demand ffmpeg publisher looping a validated cached asset from the media mount."""
    try:
        _media_file_path_adapter.validate_python(source_url)
    except ValidationError:
        logger.warning("unsafe media file path %r; leaving path sourceless", source_url)

        return {}

    input_path = posixpath.join(settings.media_mount_dir, source_url)

    return {
        "runOnDemand": _FILE_PUBLISH_COMMAND.format(input=input_path),
        "runOnDemandRestart": True,
        "runOnDemandStartTimeout": "10s",
        "runOnDemandCloseAfter": "10s",
    }


def _path_body(source_type: CameraSource, source_url: str | None) -> dict[str, Any]:
    """Build a mediamtx path config for the camera's ingest type."""
    if source_type == CameraSource.WEBRTC:
        return {}

    if source_url is None:
        return {}

    if source_type == CameraSource.FILE:
        return _file_path_body(source_url)

    source = _pull_source(source_type, source_url)
    if source is None:
        return {}

    return {
        "source": source,
        "sourceOnDemand": True,
        "sourceOnDemandStartTimeout": "10s",
        "sourceOnDemandCloseAfter": "10s",
    }


async def upsert_camera_path(
    camera_id: UUID, source_type: CameraSource, source_url: str | None
) -> None:
    """Create or replace the camera's mediamtx path so it ingests the camera feed.

    Raises `httpx.HTTPError` on failure — callers decide how to surface it.
    """
    name = camera_path_name(camera_id)
    body = _path_body(source_type, source_url)

    response = await client.post(
        f"{_API_BASE}/v3/config/paths/add/{name}", json=body, timeout=_PATH_TIMEOUT
    )
    if response.status_code == 400:
        # Path already exists — patch it in place.
        response = await client.patch(
            f"{_API_BASE}/v3/config/paths/patch/{name}", json=body, timeout=_PATH_TIMEOUT
        )

    response.raise_for_status()


async def list_path_names() -> set[str]:
    """Names of the currently configured mediamtx paths.

    Raises `httpx.HTTPError` on failure — callers decide how to surface it.
    """
    names: set[str] = set()
    page = 0

    while True:
        response = await client.get(
            f"{_API_BASE}/v3/config/paths/list",
            params={"itemsPerPage": 1000, "page": page},
            timeout=_PATH_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        items = payload["items"]
        names.update(item["name"] for item in items)

        page += 1
        if page >= int(payload["pageCount"]) or not items:
            break

    return names


async def delete_camera_path(camera_id: UUID) -> None:
    """Remove the camera's mediamtx path."""
    name = camera_path_name(camera_id)

    try:
        response = await client.delete(
            f"{_API_BASE}/v3/config/paths/delete/{name}", timeout=_PATH_TIMEOUT
        )
        if response.status_code not in (200, 404):
            response.raise_for_status()
    except httpx.HTTPError:
        logger.exception("mediamtx delete failed camera=%s", camera_id)
