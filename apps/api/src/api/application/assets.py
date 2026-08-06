"""Asset store orchestration: bucket listing, uploads and the playback cache.

Assets are objects in an S3-compatible bucket (Cloudflare R2 in production).
For playback an object is downloaded once into the media cache volume that
mediamtx mounts read-only. The cached name derives from the object key and
etag, so a re-uploaded asset gets a fresh cache entry and stale copies of the
same key are pruned.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import mimetypes
import re
import uuid
from pathlib import Path, PurePosixPath
from typing import TYPE_CHECKING, BinaryIO

from pydantic import TypeAdapter

from api.adapters.storage import s3
from api.config import settings
from api.domain.enums import CameraSource
from api.domain.errors import GraphErrorCode, WorkflowGraphError
from api.domain.workflow import CameraSourceData
from api.domain.workflow.sources import MediaFilePath

if TYPE_CHECKING:
    from api.adapters.storage.s3 import StoredAsset
    from api.domain.graph import WorkflowGraphIndex

logger = logging.getLogger(__name__)

_UNSAFE_KEY_CHARS = re.compile(r"[^A-Za-z0-9._-]+")
_SUFFIX_PATTERN = re.compile(r"^\.[A-Za-z0-9]{1,16}$")

_media_file_path_adapter: TypeAdapter[MediaFilePath] = TypeAdapter(MediaFilePath)


class AssetStoreNotConfiguredError(RuntimeError):
    def __init__(self) -> None:
        super().__init__("asset store is not configured — set the S3_* variables in .env")


class AssetNotFoundError(LookupError):
    def __init__(self, key: str) -> None:
        super().__init__(f"asset '{key}' not found in the bucket")
        self.key = key


def _ensure_configured() -> None:
    if not s3.asset_store_configured():
        raise AssetStoreNotConfiguredError


async def list_assets() -> list[StoredAsset]:
    _ensure_configured()

    return await s3.list_assets()


def sanitize_asset_key(filename: str) -> str:
    """Collapse an uploaded filename into a key safe for the ffmpeg command line."""
    collapsed = _UNSAFE_KEY_CHARS.sub("-", filename).strip("-._")

    if not collapsed:
        return "asset"

    return collapsed


async def upload_asset(filename: str, fileobj: BinaryIO, content_type: str) -> StoredAsset:
    _ensure_configured()

    key = sanitize_asset_key(filename)
    _media_file_path_adapter.validate_python(key)

    await s3.upload_asset(key, fileobj, content_type)

    stored = await s3.head_asset(key)
    if stored is None:
        raise AssetNotFoundError(key)

    logger.info("asset uploaded key=%s size=%s", stored.key, stored.size)

    return stored


async def delete_asset(key: str) -> None:
    _ensure_configured()

    if await s3.head_asset(key) is None:
        raise AssetNotFoundError(key)

    await s3.delete_asset(key)
    await asyncio.to_thread(_prune_cached, key, None)
    logger.info("asset deleted key=%s", key)


async def cached_asset_file(key: str) -> tuple[Path, str]:
    """Materialize the asset in the playback cache and return its path with a media type."""
    name = await ensure_cached(key)

    guessed, _encoding = mimetypes.guess_type(key)
    content_type = guessed if guessed else "application/octet-stream"

    return Path(settings.media_cache_dir) / name, content_type


def _key_hash(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _cache_name(key: str, etag: str) -> str:
    suffix = PurePosixPath(key).suffix
    if not _SUFFIX_PATTERN.match(suffix):
        suffix = ""

    etag_hash = hashlib.sha256(etag.encode()).hexdigest()[:16]

    return f"{_key_hash(key)}-{etag_hash}{suffix}"


def _prune_cached(key: str, keep: str | None) -> None:
    cache_dir = Path(settings.media_cache_dir)
    if not cache_dir.is_dir():
        return

    for stale in cache_dir.glob(f"{_key_hash(key)}-*"):
        if stale.name != keep:
            stale.unlink(missing_ok=True)
            logger.info("pruned stale cached asset %s", stale.name)


def _prepare_cache_dir() -> Path:
    cache_dir = Path(settings.media_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)

    return cache_dir


async def ensure_cached(key: str) -> str:
    """Download the asset into the media cache if needed; return the cached file name."""
    _ensure_configured()

    stored = await s3.head_asset(key)
    if stored is None:
        raise AssetNotFoundError(key)

    name = _cache_name(key, stored.etag)
    cache_dir = await asyncio.to_thread(_prepare_cache_dir)

    target = cache_dir / name
    if await asyncio.to_thread(target.exists):
        return name

    partial = cache_dir / f".{name}.{uuid.uuid4().hex}.partial"
    try:
        await s3.download_asset(key, partial)
        await asyncio.to_thread(partial.replace, target)
    finally:
        await asyncio.to_thread(partial.unlink, missing_ok=True)

    await asyncio.to_thread(_prune_cached, key, name)
    logger.info("cached asset key=%s file=%s size=%s", key, name, stored.size)

    return name


async def validate_assets_available(index: WorkflowGraphIndex) -> None:
    """Every file camera must reference an existing object in the asset store."""
    for node_id in sorted(index.nodes_by_id):
        data = index.nodes_by_id[node_id]
        if not isinstance(data, CameraSourceData):
            continue

        if data.source_type != CameraSource.FILE:
            continue

        if not s3.asset_store_configured():
            raise WorkflowGraphError(GraphErrorCode.ASSET_STORE_NOT_CONFIGURED, node_id=node_id)

        if await s3.head_asset(data.url) is None:
            raise WorkflowGraphError(
                GraphErrorCode.ASSET_UNAVAILABLE, node_id=node_id, key=data.url
            )
