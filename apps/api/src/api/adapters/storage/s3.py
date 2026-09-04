"""S3-compatible object storage for video assets, built against Cloudflare R2.

R2 speaks the S3 API at https://<account_id>.r2.cloudflarestorage.com and
expects region "auto". Checksums are pinned to "when_required": boto3 1.36+
computes CRC32 request checksums by default and not every S3-compatible store
accepts them. boto3 is synchronous, so every wrapper runs it in a thread.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING, Any, BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from api.application.errors import AssetStoreUnavailableError
from api.config import settings

if TYPE_CHECKING:
    from collections.abc import Callable
    from datetime import datetime
    from pathlib import Path

_MISSING_OBJECT_CODES = {"404", "NoSuchKey", "NotFound"}
logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class StoredAsset:
    etag: str
    key: str
    last_modified: datetime
    size: int


def asset_store_configured() -> bool:
    return bool(settings.s3_endpoint_url) and bool(settings.s3_bucket)


@cache
def _client() -> Any:
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name=settings.s3_region,
        config=Config(
            connect_timeout=5,
            read_timeout=30,
            retries={"mode": "standard", "total_max_attempts": 3},
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )


async def _run_operation[Result](
    operation: Callable[..., Result], *args: Any, **kwargs: Any
) -> Result:
    try:
        return await asyncio.to_thread(operation, *args, **kwargs)
    except (BotoCoreError, ClientError, OSError) as error:
        logger.warning("asset storage operation failed error=%s", type(error).__name__)
        raise AssetStoreUnavailableError from None


def _object_key(key: str) -> str:
    return f"{settings.s3_prefix}{key}"


def _stored_asset(key: str, size: int, etag: str, last_modified: datetime) -> StoredAsset:
    return StoredAsset(key=key, size=size, etag=etag.strip('"'), last_modified=last_modified)


def _list_assets_sync() -> list[StoredAsset]:
    paginator = _client().get_paginator("list_objects_v2")
    prefix = settings.s3_prefix

    assets: list[StoredAsset] = []
    for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix=prefix):
        for entry in page.get("Contents", []):
            key = entry["Key"].removeprefix(prefix)
            if not key:
                continue

            assets.append(_stored_asset(key, entry["Size"], entry["ETag"], entry["LastModified"]))

    assets.sort(key=lambda asset: asset.key)

    return assets


async def list_assets() -> list[StoredAsset]:
    return await _run_operation(_list_assets_sync)


def _head_asset_sync(key: str) -> StoredAsset | None:
    try:
        response = _client().head_object(Bucket=settings.s3_bucket, Key=_object_key(key))
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") in _MISSING_OBJECT_CODES:
            return None

        raise

    return _stored_asset(key, response["ContentLength"], response["ETag"], response["LastModified"])


async def head_asset(key: str) -> StoredAsset | None:
    return await _run_operation(_head_asset_sync, key)


async def upload_asset(key: str, fileobj: BinaryIO, content_type: str) -> None:
    await _run_operation(
        lambda: _client().upload_fileobj(
            fileobj,
            settings.s3_bucket,
            _object_key(key),
            ExtraArgs={"ContentType": content_type},
        ),
    )


async def download_asset(key: str, destination: Path) -> None:
    await _run_operation(
        lambda: _client().download_file(settings.s3_bucket, _object_key(key), str(destination))
    )


async def delete_asset(key: str) -> None:
    await _run_operation(
        lambda: _client().delete_object(Bucket=settings.s3_bucket, Key=_object_key(key))
    )


def _ensure_bucket_sync() -> None:
    client = _client()
    try:
        client.head_bucket(Bucket=settings.s3_bucket)
        return
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") not in {"404", "NoSuchBucket", "NotFound"}:
            raise

    try:
        client.create_bucket(Bucket=settings.s3_bucket)
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") != "BucketAlreadyOwnedByYou":
            raise


async def ensure_bucket() -> None:
    await _run_operation(_ensure_bucket_sync)
