"""Enterprise notification delivery adapters."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import httpx

from api.adapters.actions.formatting import format_template
from api.adapters.http.client import client
from api.adapters.http.delivery_errors import http_delivery_error
from api.adapters.persistence.credentials import read_credential_payload
from api.application.errors import DeliveryError
from api.domain.credentials import SlackWebhookPayload

if TYPE_CHECKING:
    from api.application.execution import ExecutionIdentity
    from api.domain.events import DetectionEvent
    from ee.workflow.actions import SlackActionData

logger = logging.getLogger(__name__)


async def run_slack(
    identity: ExecutionIdentity,
    event: DetectionEvent,
    config: SlackActionData,
    context: dict[str, Any],
) -> None:
    credential = await read_credential_payload(config.credential_id, SlackWebhookPayload)
    if credential is None:
        logger.warning("slack credential unavailable node=%s; skipping", identity.node_id)
        raise DeliveryError("slack credential unavailable", retryable=False)

    message = format_template(config.message_template, event, context)

    # The webhook URL embeds its token, so failures must not log it.
    try:
        response = await client.post(
            str(credential.webhook_url), json={"text": message}, timeout=10
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("slack delivery failed workflow=%s", identity.workflow_id)
        raise http_delivery_error(exc) from None
