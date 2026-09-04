"""S3 adapter behaviour around a stubbed boto3 client."""

from datetime import UTC, datetime
from io import BytesIO

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from api.adapters.storage import s3
from api.adapters.storage.s3 import StoredAsset
from api.application.errors import AssetStoreUnavailableError
from api.config import settings

MODIFIED = datetime(2026, 1, 1, tzinfo=UTC)


class StubPaginator:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def paginate(self, **kwargs):
        self.calls.append(kwargs)

        return iter(self.pages)


class StubClient:
    def __init__(self):
        self.calls = []
        self.head_response = {"ContentLength": 12, "ETag": '"abc"', "LastModified": MODIFIED}
        self.head_error = None
        self.paginator = StubPaginator([])
        self.bucket_error = None
        self.create_error = None

    def head_bucket(self, **kwargs):
        self.calls.append(("head_bucket", kwargs))
        if self.bucket_error is not None:
            raise self.bucket_error

    def create_bucket(self, **kwargs):
        self.calls.append(("create_bucket", kwargs))
        if self.create_error is not None:
            raise self.create_error

    def head_object(self, **kwargs):
        self.calls.append(("head_object", kwargs))
        if self.head_error is not None:
            raise self.head_error

        return self.head_response

    def get_paginator(self, name):
        self.calls.append(("get_paginator", name))

        return self.paginator

    def upload_fileobj(self, fileobj, bucket, key, **kwargs):
        self.calls.append(("upload_fileobj", fileobj.read(), bucket, key, kwargs))

    def download_file(self, bucket, key, destination):
        self.calls.append(("download_file", bucket, key, destination))

    def delete_object(self, **kwargs):
        self.calls.append(("delete_object", kwargs))


def client_error(code):
    return ClientError({"Error": {"Code": code, "Message": code}}, "HeadObject")


@pytest.fixture
def stub(monkeypatch):
    client = StubClient()
    monkeypatch.setattr(s3, "_client", lambda: client)
    monkeypatch.setattr(settings, "s3_endpoint_url", "https://acc.r2.cloudflarestorage.com")
    monkeypatch.setattr(settings, "s3_bucket", "media")
    monkeypatch.setattr(settings, "s3_prefix", "assets/")

    return client


@pytest.mark.parametrize(
    ("endpoint", "bucket", "expected"),
    [
        ("https://r2", "media", True),
        ("", "media", False),
        ("https://r2", "", False),
        ("", "", False),
    ],
)
def test_store_is_configured_only_with_endpoint_and_bucket(monkeypatch, endpoint, bucket, expected):
    monkeypatch.setattr(settings, "s3_endpoint_url", endpoint)
    monkeypatch.setattr(settings, "s3_bucket", bucket)

    assert s3.asset_store_configured() is expected


async def test_head_strips_etag_quotes_and_prefixes_the_key(stub):
    asset = await s3.head_asset("clips/lobby.mp4")

    assert asset == StoredAsset(etag="abc", key="clips/lobby.mp4", last_modified=MODIFIED, size=12)
    assert stub.calls == [("head_object", {"Bucket": "media", "Key": "assets/clips/lobby.mp4"})]


@pytest.mark.parametrize("code", ["404", "NoSuchKey", "NotFound"])
async def test_head_of_missing_object_is_none(stub, code):
    stub.head_error = client_error(code)

    assert await s3.head_asset("ghost.mp4") is None


async def test_head_translates_storage_failures(stub):
    stub.head_error = client_error("AccessDenied")

    with pytest.raises(AssetStoreUnavailableError):
        await s3.head_asset("secret.mp4")


@pytest.mark.parametrize("operation", ["list", "head", "upload", "download", "delete"])
@pytest.mark.parametrize("failure", ["credentials", "connection"])
async def test_storage_failures_are_sanitized(monkeypatch, tmp_path, operation, failure, caplog):
    def unavailable():
        if failure == "credentials":
            raise ClientError(
                {"Error": {"Code": "InvalidAccessKeyId", "Message": "private-access-key"}},
                "ListObjectsV2",
            )

        raise EndpointConnectionError(endpoint_url="https://private-access-key@storage.example")

    monkeypatch.setattr(s3, "_client", unavailable)
    operations = {
        "list": lambda: s3.list_assets(),
        "head": lambda: s3.head_asset("clip.mp4"),
        "upload": lambda: s3.upload_asset("clip.mp4", BytesIO(b"video"), "video/mp4"),
        "download": lambda: s3.download_asset("clip.mp4", tmp_path / "video"),
        "delete": lambda: s3.delete_asset("clip.mp4"),
    }

    with pytest.raises(AssetStoreUnavailableError) as caught:
        await operations[operation]()

    assert "private-access-key" not in str(caught.value)
    assert "private-access-key" not in caplog.text


async def test_list_strips_the_prefix_skips_the_folder_marker_and_sorts(stub):
    stub.paginator = StubPaginator(
        [
            {
                "Contents": [
                    {"Key": "assets/zebra.mp4", "Size": 2, "ETag": '"z"', "LastModified": MODIFIED},
                    {"Key": "assets/", "Size": 0, "ETag": '"m"', "LastModified": MODIFIED},
                ]
            },
            {
                "Contents": [
                    {"Key": "assets/apple.mp4", "Size": 1, "ETag": '"a"', "LastModified": MODIFIED}
                ]
            },
            {},
        ]
    )

    assets = await s3.list_assets()

    assert [asset.key for asset in assets] == ["apple.mp4", "zebra.mp4"]
    assert stub.paginator.calls == [{"Bucket": "media", "Prefix": "assets/"}]


async def test_upload_sets_the_content_type(stub):
    await s3.upload_asset("clip.mp4", BytesIO(b"abc"), "video/mp4")

    assert stub.calls == [
        (
            "upload_fileobj",
            b"abc",
            "media",
            "assets/clip.mp4",
            {"ExtraArgs": {"ContentType": "video/mp4"}},
        )
    ]


async def test_download_targets_the_destination_path(stub, tmp_path):
    await s3.download_asset("clip.mp4", tmp_path / "clip.partial")

    assert stub.calls == [
        ("download_file", "media", "assets/clip.mp4", str(tmp_path / "clip.partial"))
    ]


async def test_delete_addresses_the_prefixed_key(stub):
    await s3.delete_asset("clip.mp4")

    assert stub.calls == [("delete_object", {"Bucket": "media", "Key": "assets/clip.mp4"})]


async def test_existing_bucket_is_kept(stub):
    await s3.ensure_bucket()

    assert stub.calls == [("head_bucket", {"Bucket": "media"})]


@pytest.mark.parametrize("code", ["404", "NoSuchBucket", "NotFound"])
async def test_missing_bucket_is_created(stub, code):
    stub.bucket_error = client_error(code)

    await s3.ensure_bucket()

    assert stub.calls == [
        ("head_bucket", {"Bucket": "media"}),
        ("create_bucket", {"Bucket": "media"}),
    ]


async def test_bucket_creation_is_idempotent_under_concurrency(stub):
    stub.bucket_error = client_error("404")
    stub.create_error = client_error("BucketAlreadyOwnedByYou")

    await s3.ensure_bucket()


async def test_bucket_permission_failure_does_not_attempt_creation(stub):
    stub.bucket_error = client_error("AccessDenied")

    with pytest.raises(AssetStoreUnavailableError):
        await s3.ensure_bucket()

    assert stub.calls == [("head_bucket", {"Bucket": "media"})]


async def test_bucket_owned_by_another_account_is_rejected(stub):
    stub.bucket_error = client_error("404")
    stub.create_error = client_error("BucketAlreadyExists")

    with pytest.raises(AssetStoreUnavailableError):
        await s3.ensure_bucket()
