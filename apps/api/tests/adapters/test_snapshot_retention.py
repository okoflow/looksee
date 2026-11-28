"""Expired snapshot files are removed; everything else stays."""

import os
from datetime import UTC, datetime, timedelta

from api.adapters.filesystem.snapshots import SnapshotFileRetention

NOW = datetime(2026, 11, 26, 12, 0, tzinfo=UTC)


def write(path, age):
    path.write_bytes(b"jpeg")
    stamp = (NOW - age).timestamp()
    os.utime(path, (stamp, stamp))
    return path


async def test_removes_only_snapshots_older_than_the_cutoff(tmp_path):
    old = write(tmp_path / "old.jpg", timedelta(days=31))
    fresh = write(tmp_path / "fresh.jpg", timedelta(days=1))
    other = write(tmp_path / "notes.txt", timedelta(days=365))
    nested_dir = tmp_path / "nested"
    nested_dir.mkdir()
    nested = write(nested_dir / "old.jpg", timedelta(days=365))

    removed = await SnapshotFileRetention(tmp_path).purge(NOW - timedelta(days=30))

    assert removed == 1
    assert not old.exists()
    assert fresh.exists()
    assert other.exists()
    assert nested.exists()


async def test_missing_directory_removes_nothing(tmp_path):
    removed = await SnapshotFileRetention(tmp_path / "absent").purge(NOW)

    assert removed == 0
