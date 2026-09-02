"""Stable string values of the domain enums."""

import pytest

from api.domain.enums import AlertSeverity, CameraSource, CameraStatus


@pytest.mark.parametrize(
    ("enum", "expected"),
    [
        (AlertSeverity, ("info", "warning", "critical")),
        (CameraSource, ("rtsp", "rtmp", "srt", "webrtc", "whep", "file")),
        (CameraStatus, ("pending", "active", "error", "disabled")),
    ],
)
def test_values_are_stable(enum, expected):
    values = tuple(member.value for member in enum)

    assert values == expected


def test_members_compare_equal_to_their_strings():
    assert CameraSource.RTSP == "rtsp"
    assert AlertSeverity.CRITICAL == "critical"


def test_lookup_by_value_returns_the_member():
    assert CameraStatus("disabled") is CameraStatus.DISABLED


def test_unknown_value_is_rejected():
    with pytest.raises(ValueError, match="unknown"):
        CameraStatus("unknown")
