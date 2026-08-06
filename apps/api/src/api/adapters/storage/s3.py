"""S3-compatible object storage for video assets, built against Cloudflare R2.

R2 speaks the S3 API at https://<account_id>.r2.cloudflarestorage.com and
expects region "auto". Checksums are pinned to "when_required": boto3 1.36+
computes CRC32 request checksums by default and not every S3-compatible store
accepts them. boto3 is synchronous, so every wrapper runs it in a thread.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING, Any, BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from api.config import settings

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

_MISSING_OBJECT_CODES = {"404", "NoSuchKey", "NotFound"}


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
            request_checksum_calculation="when_required",
            response_checksum_validation="when_required",
        ),
    )


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
    return await asyncio.to_thread(_list_assets_sync)


def _head_asset_sync(key: str) -> StoredAsset | None:
    try:
        response = _client().head_object(Bucket=settings.s3_bucket, Key=_object_key(key))
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") in _MISSING_OBJECT_CODES:
            return None

        raise

    return _stored_asset(key, response["ContentLength"], response["ETag"], response["LastModified"])


async def head_asset(key: str) -> StoredAsset | None:
    return await asyncio.to_thread(_head_asset_sync, key)


async def upload_asset(key: str, fileobj: BinaryIO, content_type: str) -> None:
    await asyncio.to_thread(
        _client().upload_fileobj,
        fileobj,
        settings.s3_bucket,
        _object_key(key),
        ExtraArgs={"ContentType": content_type},
    )


async def download_asset(key: str, destination: Path) -> None:
    await asyncio.to_thread(
        _client().download_file, settings.s3_bucket, _object_key(key), str(destination)
    )


async def delete_asset(key: str) -> None:
    await asyncio.to_thread(
        _client().delete_object, Bucket=settings.s3_bucket, Key=_object_key(key)
    )
