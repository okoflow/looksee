"""Asset store endpoints with the S3 adapter stubbed out."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from api.adapters.storage import s3
from api.adapters.storage.s3 import StoredAsset
from api.config import settings

MODIFIED = datetime(2026, 1, 1, tzinfo=UTC)


def write_file(destination, body):
    Path(destination).write_bytes(body)


@pytest.fixture
def store(monkeypatch, tmp_path, owner):
    objects = {}

    async def head_asset(key):
        return objects.get(key)

    async def list_assets():
        return [objects[key] for key in sorted(objects)]

    async def upload_asset(key, fileobj, content_type):
        objects[key] = StoredAsset(
            etag="e1", key=key, last_modified=MODIFIED, size=len(fileobj.read())
        )

    async def download_asset(key, destination):
        write_file(destination, b"video-bytes")

    async def delete_asset(key):
        objects.pop(key)

    monkeypatch.setattr(s3, "asset_store_configured", lambda: True)
    monkeypatch.setattr(s3, "head_asset", head_asset)
    monkeypatch.setattr(s3, "list_assets", list_assets)
    monkeypatch.setattr(s3, "upload_asset", upload_asset)
    monkeypatch.setattr(s3, "download_asset", download_asset)
    monkeypatch.setattr(s3, "delete_asset", delete_asset)
    monkeypatch.setattr(settings, "media_cache_dir", str(tmp_path / "cache"))

    return objects


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", "/assets"), ("DELETE", "/assets/clip.mp4"), ("GET", "/assets/clip.mp4/content")],
)
def test_unconfigured_store_is_service_unavailable(client, owner, monkeypatch, method, path):
    monkeypatch.setattr(s3, "asset_store_configured", lambda: False)

    response = client.request(method, path)

    assert response.status_code == 503
    assert "asset store is not configured" in response.json()["detail"]


def test_unconfigured_store_refuses_uploads(client, owner, monkeypatch):
    monkeypatch.setattr(s3, "asset_store_configured", lambda: False)

    response = client.post("/assets", files={"file": ("clip.mp4", b"abc", "video/mp4")})

    assert response.status_code == 503


def test_upload_then_list(client, store):
    uploaded = client.post("/assets", files={"file": ("my clip.mp4", b"abc", "video/mp4")})

    listed = client.get("/assets")

    assert uploaded.status_code == 201
    assert uploaded.json() == {
        "key": "my-clip.mp4",
        "size": 3,
        "etag": "e1",
        "last_modified": "2026-01-01T00:00:00Z",
    }
    assert listed.json() == [uploaded.json()]


def test_content_is_served_from_the_playback_cache(client, store):
    store["clips/lobby.mp4"] = StoredAsset(
        etag="e1", key="clips/lobby.mp4", last_modified=MODIFIED, size=11
    )

    response = client.get("/assets/clips/lobby.mp4/content")

    assert response.status_code == 200
    assert response.content == b"video-bytes"
    assert response.headers["content-type"] == "video/mp4"


def test_missing_asset_content_is_not_found(client, store):
    response = client.get("/assets/ghost.mp4/content")

    assert response.status_code == 404
    assert response.json() == {"detail": "asset 'ghost.mp4' not found in the bucket"}


def test_delete_asset(client, store):
    store["clip.mp4"] = StoredAsset(etag="e1", key="clip.mp4", last_modified=MODIFIED, size=1)

    assert client.delete("/assets/clip.mp4").status_code == 204
    assert client.delete("/assets/clip.mp4").status_code == 404
    assert store == {}
