"""Delete snapshot files past their retention."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path

logger = logging.getLogger(__name__)


class SnapshotFileRetention:
    """Snapshots are flat `*.jpg` files; their modification time is their capture time."""

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    async def purge(self, cutoff: datetime) -> int:
        return await asyncio.to_thread(self._purge, cutoff.timestamp())

    def _purge(self, cutoff: float) -> int:
        if not self._directory.is_dir():
            return 0

        removed = 0
        for path in self._directory.glob("*.jpg"):
            try:
                if path.is_file() and path.stat().st_mtime < cutoff:
                    path.unlink()
                    removed += 1
            except FileNotFoundError:
                continue
            except OSError:
                logger.warning("could not remove expired snapshot %s", path.name)

        return removed
