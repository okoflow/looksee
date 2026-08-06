"""Runtime dependencies a filter needs to evaluate one event."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID
    from zoneinfo import ZoneInfo


class RuntimeState(Protocol):
    def swap_track_point(
        self,
        workflow_id: UUID,
        run_id: UUID,
        node_id: str,
        camera_id: UUID,
        tracker_id: int,
        point: tuple[float, float],
        now: datetime,
    ) -> tuple[float, float] | None: ...

    def dwell_seconds(
        self,
        workflow_id: UUID,
        run_id: UUID,
        node_id: str,
        camera_id: UUID,
        tracker_id: int,
        inside: bool,
        now: datetime,
    ) -> float: ...

    def debounce_allows(
        self,
        workflow_id: UUID,
        run_id: UUID,
        node_id: str,
        camera_id: UUID,
        seconds: int,
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class FilterRuntime:
    """Per-node evaluation context handed to every filter's `passes`."""

    workflow_id: UUID
    run_id: UUID
    node_id: str
    timezone: ZoneInfo
    state: RuntimeState
