"""Periodic removal of stored evidence older than its configured retention."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

logger = logging.getLogger(__name__)

type Purge = Callable[[datetime], Awaitable[int]]


@dataclass(frozen=True, slots=True)
class RetentionRule:
    """Delete one kind of record older than `days`; 0 keeps it forever."""

    name: str
    days: int
    purge: Purge


async def purge_expired(
    rules: Sequence[RetentionRule],
    *,
    now: datetime | None = None,
) -> dict[str, int]:
    """Run every enabled rule once and return how many records each removed."""
    moment = now or datetime.now(UTC)
    removed: dict[str, int] = {}

    for rule in rules:
        if rule.days <= 0:
            continue

        count = await rule.purge(moment - timedelta(days=rule.days))
        removed[rule.name] = count
        if count:
            logger.info("retention removed %d %s older than %d days", count, rule.name, rule.days)

    return removed


async def run_retention_loop(interval_seconds: float, rules: Sequence[RetentionRule]) -> None:
    while True:
        try:
            await purge_expired(rules)
        except Exception:
            logger.exception("retention tick failed")
        await asyncio.sleep(interval_seconds)
