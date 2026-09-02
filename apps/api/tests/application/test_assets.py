"""Asset store orchestration with a stubbed S3 adapter and a temporary playback cache."""

from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

import pytest

from api.adapters.storage import s3
from api.adapters.storage.s3 import StoredAsset
from api.application import assets
from api.application.assets import (
    AssetNotFoundError,
    AssetStoreNotConfiguredError,
    sanitize_asset_key,
)
from api.config import settings
from api.domain.errors import GraphErrorCode, WorkflowGraphError
from api.domain.graph import WorkflowGraphIndex

MODIFIED = datetime(2026, 1, 1, tzinfo=UTC)


def write_file(destination, body):
    Path(destination).write_bytes(body)


class StubStore:
    def __init__(self):
        self.objects = {}
        self.downloads = []
        self.uploads = []
        self.deleted = []
        self.configured = True

    def put(self, key, etag="etag-1", body=b"video-bytes"):
        self.objects[key] = (
            StoredAsset(etag=etag, key=key, last_modified=MODIFIED, size=len(body)),
            body,
        )

        return self.objects[key][0]


@pytest.fixture
def store(monkeypatch, tmp_path):
    stub = StubStore()

    async def head_asset(key):
        entry = stub.objects.get(key)

        return entry[0] if entry is not None else None

    async def download_asset(key, destination):
        stub.downloads.append(key)
        write_file(destination, stub.objects[key][1])

    async def upload_asset(key, fileobj, content_type):
        stub.uploads.append((key, fileobj.read(), content_type))
        stub.put(key, body=stub.uploads[-1][1])

    async def delete_asset(key):
        stub.deleted.append(key)
        stub.objects.pop(key, None)

    async def list_assets():
        return [entry[0] for _key, entry in sorted(stub.objects.items())]

    monkeypatch.setattr(s3, "asset_store_configured", lambda: stub.configured)
    monkeypatch.setattr(s3, "head_asset", head_asset)
    monkeypatch.setattr(s3, "download_asset", download_asset)
    monkeypatch.setattr(s3, "upload_asset", upload_asset)
    monkeypatch.setattr(s3, "delete_asset", delete_asset)
    monkeypatch.setattr(s3, "list_assets", list_assets)
    monkeypatch.setattr(settings, "media_cache_dir", str(tmp_path / "cache"))

    return stub


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("lobby.mp4", "lobby.mp4"),
        ("my clip (1).MOV", "my-clip-1-.MOV"),
        ("../../etc/passwd", "etc-passwd"),
        ("  .hidden.mp4", "hidden.mp4"),
        ("***", "asset"),
        ("", "asset"),
        ("straße.mp4", "stra-e.mp4"),
    ],
)
def test_sanitize_asset_key_produces_shell_safe_keys(filename, expected):
    assert sanitize_asset_key(filename) == expected


@pytest.mark.parametrize("operation", [assets.list_assets, assets.ensure_cached])
async def test_operations_fail_fast_when_store_is_not_configured(store, operation):
    store.configured = False

    with pytest.raises(AssetStoreNotConfiguredError, match="S3_"):
        await operation("any.mp4") if operation is assets.ensure_cached else await operation()


async def test_ensure_cached_downloads_once_under_a_key_and_etag_derived_name(store, tmp_path):
    store.put("clips/lobby.mp4")

    first = await assets.ensure_cached("clips/lobby.mp4")
    second = await assets.ensure_cached("clips/lobby.mp4")

    cached = tmp_path / "cache" / first
    assert first == second
    assert first.endswith(".mp4")
    assert "/" not in first
    assert cached.read_bytes() == b"video-bytes"
    assert store.downloads == ["clips/lobby.mp4"]
    assert list((tmp_path / "cache").iterdir()) == [cached]


async def test_re_uploaded_asset_gets_a_fresh_cache_entry_and_stale_copies_are_pruned(
    store, tmp_path
):
    store.put("lobby.mp4", etag="v1")
    stale = await assets.ensure_cached("lobby.mp4")
    store.put("lobby.mp4", etag="v2", body=b"new-bytes")

    fresh = await assets.ensure_cached("lobby.mp4")

    assert fresh != stale
    assert fresh.split("-")[0] == stale.split("-")[0]
    assert [path.name for path in (tmp_path / "cache").iterdir()] == [fresh]


async def test_ensure_cached_drops_suspicious_suffixes(store):
    store.put("archive.tar.veryveryverylongsuffix")

    name = await assets.ensure_cached("archive.tar.veryveryverylongsuffix")

    assert "." not in name


async def test_ensure_cached_reports_missing_objects(store):
    with pytest.raises(AssetNotFoundError, match=r"'ghost\.mp4' not found"):
        await assets.ensure_cached("ghost.mp4")


async def test_cached_asset_file_guesses_the_media_type(store, tmp_path):
    store.put("lobby.mp4")
    store.put("blob.weird")

    video_path, video_type = await assets.cached_asset_file("lobby.mp4")
    _blob_path, blob_type = await assets.cached_asset_file("blob.weird")

    assert video_path.parent == tmp_path / "cache"
    assert video_type == "video/mp4"
    assert blob_type == "application/octet-stream"


async def test_upload_sanitizes_the_key_and_returns_the_stored_object(store):
    stored = await assets.upload_asset("my clip.mp4", BytesIO(b"abc"), "video/mp4")

    assert stored.key == "my-clip.mp4"
    assert stored.size == 3
    assert store.uploads == [("my-clip.mp4", b"abc", "video/mp4")]


async def test_upload_that_never_lands_is_reported(store, monkeypatch):
    async def head_nothing(key):
        return None

    monkeypatch.setattr(s3, "head_asset", head_nothing)

    with pytest.raises(AssetNotFoundError):
        await assets.upload_asset("clip.mp4", BytesIO(b"abc"), "video/mp4")


async def test_delete_removes_object_and_cached_copies(store, tmp_path):
    store.put("lobby.mp4")
    cached_name = await assets.ensure_cached("lobby.mp4")

    await assets.delete_asset("lobby.mp4")

    assert store.deleted == ["lobby.mp4"]
    assert not (tmp_path / "cache" / cached_name).exists()


async def test_delete_of_missing_object_is_reported(store):
    with pytest.raises(AssetNotFoundError):
        await assets.delete_asset("ghost.mp4")

    assert store.deleted == []


async def test_list_assets_proxies_the_store(store):
    lobby = store.put("lobby.mp4")

    assert await assets.list_assets() == [lobby]


class TestValidateAssetsAvailable:
    def index(self, build_graph, basic_nodes, source_type="file", url="clips/lobby.mp4"):
        basic_nodes["cam"].update({"source_type": source_type, "url": url})

        return WorkflowGraphIndex.build(
            build_graph(basic_nodes, [("cam", "det"), ("det", "alert")])
        )

    async def test_non_file_sources_are_not_checked(self, store, build_graph, basic_nodes):
        store.configured = False

        await assets.validate_assets_available(
            self.index(build_graph, basic_nodes, "rtsp", "rtsp://cam/stream")
        )

    async def test_file_source_needs_a_configured_store(self, store, build_graph, basic_nodes):
        store.configured = False

        with pytest.raises(WorkflowGraphError) as excinfo:
            await assets.validate_assets_available(self.index(build_graph, basic_nodes))

        assert excinfo.value.code is GraphErrorCode.ASSET_STORE_NOT_CONFIGURED
        assert excinfo.value.node_id == "cam"

    async def test_file_source_needs_an_existing_object(self, store, build_graph, basic_nodes):
        with pytest.raises(WorkflowGraphError) as excinfo:
            await assets.validate_assets_available(self.index(build_graph, basic_nodes))

        assert excinfo.value.code is GraphErrorCode.ASSET_UNAVAILABLE
        assert "'clips/lobby.mp4'" in str(excinfo.value)

    async def test_existing_object_passes(self, store, build_graph, basic_nodes):
        store.put("clips/lobby.mp4")

        await assets.validate_assets_available(self.index(build_graph, basic_nodes))
