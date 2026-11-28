"""Retention rules: which records expire and when."""

from datetime import UTC, datetime, timedelta

import pytest

from api.application import retention
from api.application.retention import RetentionRule, purge_expired, run_retention_loop

NOW = datetime(2026, 11, 26, 12, 0, tzinfo=UTC)


class StopLoopError(Exception):
    pass


def recording_rule(name, days, removed=0):
    cutoffs = []

    async def purge(cutoff):
        cutoffs.append(cutoff)
        return removed

    return RetentionRule(name, days, purge), cutoffs


async def test_enabled_rule_purges_before_its_cutoff():
    rule, cutoffs = recording_rule("alerts", 30, removed=4)

    removed = await purge_expired([rule], now=NOW)

    assert cutoffs == [NOW - timedelta(days=30)]
    assert removed == {"alerts": 4}


async def test_zero_days_keeps_records_forever():
    rule, cutoffs = recording_rule("snapshots", 0)

    removed = await purge_expired([rule], now=NOW)

    assert cutoffs == []
    assert removed == {}


async def test_each_rule_uses_its_own_period():
    snapshots, snapshot_cutoffs = recording_rule("snapshots", 7)
    alerts, alert_cutoffs = recording_rule("alerts", 90)

    await purge_expired([snapshots, alerts], now=NOW)

    assert snapshot_cutoffs == [NOW - timedelta(days=7)]
    assert alert_cutoffs == [NOW - timedelta(days=90)]


async def test_loop_survives_a_failed_tick(monkeypatch):
    calls = 0

    async def flaky(cutoff):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("database unavailable")
        return 0

    sleeps = 0

    async def fake_sleep(seconds):
        nonlocal sleeps
        sleeps += 1
        if sleeps == 2:
            raise StopLoopError

    monkeypatch.setattr(retention.asyncio, "sleep", fake_sleep)

    with pytest.raises(StopLoopError):
        await run_retention_loop(60, [RetentionRule("alerts", 1, flaky)])

    assert calls == 2
