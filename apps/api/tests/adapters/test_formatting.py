"""Event payload shape and user-template formatting."""

import pytest

from api.adapters.actions.formatting import event_payload, format_template, humanize_event_kind


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("PERSON_DETECTED", "Person"),
        ("TRAFFIC_LIGHT_RED_DETECTED", "Traffic Light Red"),
        ("SMOKE", "Smoke"),
        ("CLASS_123_DETECTED", "Class 123"),
    ],
)
def test_humanize_event_kind_reads_like_a_title(kind, expected):
    assert humanize_event_kind(kind) == expected


def test_template_fills_every_supported_placeholder(make_event):
    event = make_event(metadata={"count": 3})
    template = "{kind}|{camera_id}|{ts}|{count}|{snapshot_url}"

    rendered = format_template(template, event, {"snapshot_url": "/snapshots/a.jpg"})

    assert rendered == (
        f"PERSON_DETECTED|{event.camera_id}|{event.ts.isoformat()}|3|/snapshots/a.jpg"
    )


def test_count_falls_back_to_detection_count_and_snapshot_to_empty(make_event, make_detection):
    event = make_event(metadata={}, detections=[make_detection(), make_detection()])

    assert format_template("{count}:{snapshot_url}", event, {}) == "2:"


@pytest.mark.parametrize("template", ["{unknown}", "{}", "{count:d}", "{kind"])
def test_invalid_templates_are_sent_verbatim_with_a_warning(make_event, template, caplog):
    rendered = format_template(template, make_event(), {})

    assert rendered == template
    assert "invalid placeholders" in caplog.text


def test_event_payload_has_a_stable_shape(make_event):
    event = make_event()

    payload = event_payload(event, {})

    assert payload == {
        "camera_id": str(event.camera_id),
        "kind": "PERSON_DETECTED",
        "ts": event.ts.isoformat(),
        "metadata": {"count": 1, "model_id": "people"},
    }


def test_event_payload_includes_snapshot_only_when_taken(make_event):
    event = make_event()

    with_snapshot = event_payload(event, {"snapshot_url": "/snapshots/a.jpg"})

    assert with_snapshot["snapshot_url"] == "/snapshots/a.jpg"
    assert "snapshot_url" not in event_payload(event, {"snapshot_jpeg": b"x"})


def test_event_payload_metadata_is_a_copy(make_event):
    event = make_event()

    payload = event_payload(event, {})
    payload["metadata"]["count"] = 99

    assert event.metadata["count"] == 1
