"""Snapshot persistence and optional detection annotation."""

from __future__ import annotations

import asyncio
import logging
from io import BytesIO
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from PIL import Image, ImageDraw

from api.adapters.redis.frame_store import get_last_frame
from api.config import settings

if TYPE_CHECKING:
    from api.application.execution import ExecutionIdentity
    from api.domain.events import DetectionEvent
    from api.domain.workflow import SnapshotActionData

logger = logging.getLogger(__name__)


async def run_snapshot(
    identity: ExecutionIdentity,
    event: DetectionEvent,
    config: SnapshotActionData,
    context: dict[str, Any],
) -> None:
    jpeg = await get_last_frame(event.camera_id)
    if jpeg is None:
        logger.warning("no recent frame for snapshot camera=%s", event.camera_id)
        return

    if config.annotate and event.detections:
        jpeg = await asyncio.to_thread(_annotate_jpeg, jpeg, event)

    filename = f"{event.ts:%Y%m%d-%H%M%S}-{event.camera_id.hex[:8]}-{uuid4().hex[:8]}.jpg"
    path = settings.snapshots_dir / filename
    await asyncio.to_thread(path.write_bytes, jpeg)

    context["snapshot_url"] = f"/snapshots/{filename}"
    context["snapshot_jpeg"] = jpeg


def _annotate_jpeg(jpeg: bytes, event: DetectionEvent) -> bytes:
    try:
        image = Image.open(BytesIO(jpeg)).convert("RGB")
        if image.size != (event.frame_width, event.frame_height):
            logger.warning(
                "snapshot %dx%d does not match event frame %dx%d camera=%s; keeping the raw frame",
                image.size[0],
                image.size[1],
                event.frame_width,
                event.frame_height,
                event.camera_id,
            )
            return jpeg

        draw = ImageDraw.Draw(image)
        for detection in event.detections:
            x_min, y_min, x_max, y_max = detection.bounding_box
            draw.rectangle((x_min, y_min, x_max, y_max), outline=(255, 64, 64), width=3)
            draw.text(
                (x_min + 4, max(0.0, y_min - 14)),
                detection.label,
                fill=(255, 64, 64),
            )

        output = BytesIO()
        image.save(output, format="JPEG", quality=85)

        return output.getvalue()
    except Exception:
        logger.exception("snapshot annotation failed; keeping the raw frame")

        return jpeg
