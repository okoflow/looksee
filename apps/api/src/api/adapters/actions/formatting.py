"""Stable event payload and user-template formatting."""

import logging
from typing import Any

from api.domain.events import EVENT_KIND_DETECTED_SUFFIX, DetectionEvent

logger = logging.getLogger(__name__)


def humanize_event_kind(kind: str) -> str:
    return kind.removesuffix(EVENT_KIND_DETECTED_SUFFIX).replace("_", " ").title()


def format_template(template: str, event: DetectionEvent, context: dict[str, Any]) -> str:
    """Fill the supported placeholders, degrading invalid templates to verbatim text."""
    try:
        return template.format(
            kind=event.kind,
            camera_id=str(event.camera_id),
            ts=event.ts.isoformat(),
            count=str(event.metadata.get("count", len(event.detections))),
            snapshot_url=str(context.get("snapshot_url", "")),
        )
    except (KeyError, IndexError, ValueError):
        logger.warning("template has invalid placeholders; sending it verbatim")

        return template


def event_payload(event: DetectionEvent, context: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "camera_id": str(event.camera_id),
        "kind": event.kind,
        "ts": event.ts.isoformat(),
        "metadata": dict(event.metadata),
    }
    if "snapshot_url" in context:
        payload["snapshot_url"] = context["snapshot_url"]

    return payload
