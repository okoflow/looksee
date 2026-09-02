"""Measurement filters: line crossing, dwell, and count threshold."""

from datetime import UTC, datetime, timedelta

import pytest

from ee.workflow.filters import CountThresholdFilterData, DwellFilterData, LineCrossingFilterData

T0 = datetime(2026, 3, 4, 12, 0, tzinfo=UTC)
LINE = [(0.0, 0.5), (1.0, 0.5)]
ZONE = [(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]
LEFT_HALF = [(0.0, 0.0), (0.5, 0.0), (0.5, 1.0), (0.0, 1.0)]


def at(seconds):
    return T0 + timedelta(seconds=seconds)


class TestLineCrossing:
    def test_incomplete_line_passes_everything(self, make_event, runtime):
        assert LineCrossingFilterData(line=[(0.1, 0.1)]).passes(make_event(), runtime) is True

    def test_first_observation_cannot_cross(self, make_event, make_detection, runtime):
        line = LineCrossingFilterData(line=LINE)

        assert line.passes(make_event(make_detection(center=(0.5, 0.8))), runtime) is False

    @pytest.mark.parametrize(
        ("direction", "expected"),
        [("any", True), ("in", True), ("out", False)],
    )
    def test_crossing_between_frames_is_detected_with_direction(
        self, make_event, make_detection, runtime, direction, expected
    ):
        line = LineCrossingFilterData(line=LINE, direction=direction)
        line.passes(make_event(make_detection(center=(0.5, 0.8)), ts=at(0)), runtime)

        crossed = line.passes(make_event(make_detection(center=(0.5, 0.2)), ts=at(1)), runtime)

        assert crossed is expected

    def test_movement_on_one_side_does_not_cross(self, make_event, make_detection, runtime):
        line = LineCrossingFilterData(line=LINE)
        line.passes(make_event(make_detection(center=(0.5, 0.8)), ts=at(0)), runtime)

        assert (
            line.passes(make_event(make_detection(center=(0.9, 0.7)), ts=at(1)), runtime) is False
        )

    def test_untracked_detections_are_ignored(self, make_event, make_detection, runtime):
        line = LineCrossingFilterData(line=LINE)
        line.passes(
            make_event(make_detection(center=(0.5, 0.8), tracker_id=None), ts=at(0)), runtime
        )

        crossed = line.passes(
            make_event(make_detection(center=(0.5, 0.2), tracker_id=None), ts=at(1)), runtime
        )

        assert crossed is False

    def test_tracks_are_kept_apart(self, make_event, make_detection, runtime):
        line = LineCrossingFilterData(line=LINE)
        line.passes(make_event(make_detection(center=(0.5, 0.8), tracker_id=1), ts=at(0)), runtime)

        other_track = line.passes(
            make_event(make_detection(center=(0.5, 0.2), tracker_id=2), ts=at(1)), runtime
        )

        assert other_track is False


class TestDwell:
    def test_incomplete_polygon_passes_everything(self, make_event, runtime):
        assert DwellFilterData(polygon=[(0, 0), (1, 1)]).passes(make_event(), runtime) is True

    def test_dwell_passes_once_the_track_stayed_long_enough(
        self, make_event, make_detection, runtime
    ):
        dwell = DwellFilterData(polygon=ZONE, min_seconds=60)
        inside = make_detection(center=(0.5, 0.5))

        early = dwell.passes(make_event(inside, ts=at(0)), runtime)
        almost = dwell.passes(make_event(inside, ts=at(59)), runtime)
        enough = dwell.passes(make_event(inside, ts=at(60)), runtime)

        assert (early, almost, enough) == (False, False, True)

    def test_leaving_the_zone_resets_the_clock(self, make_event, make_detection, runtime):
        dwell = DwellFilterData(polygon=LEFT_HALF, min_seconds=30)
        inside, outside = make_detection(center=(0.25, 0.5)), make_detection(center=(0.75, 0.5))
        dwell.passes(make_event(inside, ts=at(0)), runtime)
        dwell.passes(make_event(outside, ts=at(20)), runtime)
        dwell.passes(make_event(inside, ts=at(21)), runtime)

        assert dwell.passes(make_event(inside, ts=at(40)), runtime) is False
        assert dwell.passes(make_event(inside, ts=at(51)), runtime) is True

    def test_untracked_detections_never_dwell(self, make_event, make_detection, runtime):
        dwell = DwellFilterData(polygon=ZONE, min_seconds=1)
        untracked = make_detection(tracker_id=None)
        dwell.passes(make_event(untracked, ts=at(0)), runtime)

        assert dwell.passes(make_event(untracked, ts=at(5)), runtime) is False


class TestCountThreshold:
    @pytest.mark.parametrize(
        ("operator", "count", "expected"),
        [("gte", 2, True), ("gte", 3, False), ("lte", 2, True), ("lte", 1, False)],
    )
    def test_without_polygon_every_detection_counts(
        self, make_event, make_detection, runtime, operator, count, expected
    ):
        threshold = CountThresholdFilterData(operator=operator, count=count)
        event = make_event(make_detection(tracker_id=1), make_detection(tracker_id=2))

        assert threshold.passes(event, runtime) is expected

    def test_polygon_counts_only_detections_inside(self, make_event, make_detection, runtime):
        threshold = CountThresholdFilterData(polygon=LEFT_HALF, operator="gte", count=2)
        two_inside = make_event(
            make_detection(center=(0.2, 0.5), tracker_id=1),
            make_detection(center=(0.3, 0.5), tracker_id=2),
            make_detection(center=(0.8, 0.5), tracker_id=3),
        )
        one_inside = make_event(
            make_detection(center=(0.2, 0.5), tracker_id=1),
            make_detection(center=(0.8, 0.5), tracker_id=3),
        )

        assert threshold.passes(two_inside, runtime) is True
        assert threshold.passes(one_inside, runtime) is False

    def test_zero_count_with_lte_matches_an_empty_zone(self, make_event, make_detection, runtime):
        threshold = CountThresholdFilterData(polygon=LEFT_HALF, operator="lte", count=0)

        assert threshold.passes(make_event(make_detection(center=(0.8, 0.5))), runtime) is True
        assert threshold.passes(make_event(make_detection(center=(0.2, 0.5))), runtime) is False
