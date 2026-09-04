import asyncio
from pathlib import Path

from api.adapters.actions.dispatcher import dispatch_action
from api.application.deliveries import DeliveryJob
from api.application.errors import DeliveryError


class QueuedDeliverySender:
    def __init__(self, snapshots_dir: Path) -> None:
        self._snapshots_dir = snapshots_dir.resolve()

    async def __call__(self, job: DeliveryJob) -> None:
        request = job.request
        context = dict(request.context)
        context["delivery_id"] = str(job.id)
        snapshot_url = context.get("snapshot_url")
        if isinstance(snapshot_url, str):
            if not snapshot_url.startswith("/snapshots/"):
                raise DeliveryError("invalid snapshot reference", retryable=False)

            path = (self._snapshots_dir / snapshot_url.removeprefix("/snapshots/")).resolve()
            if path.parent != self._snapshots_dir:
                raise DeliveryError("invalid snapshot reference", retryable=False)
            try:
                context["snapshot_jpeg"] = await asyncio.to_thread(path.read_bytes)
            except FileNotFoundError:
                raise DeliveryError("snapshot no longer available", retryable=False) from None

        await dispatch_action(request.identity, request.event, request.action, context)
