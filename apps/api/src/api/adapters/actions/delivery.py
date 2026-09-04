"""External notification delivery adapters.

Node payloads arrive already validated by the runnable-graph check. Secrets
are resolved from the credential referenced by the node at delivery time, so a
credential edit applies immediately. Adapters report sanitized delivery errors
so the worker can distinguish permanent failures from recoverable ones.
"""

from __future__ import annotations

import json
import logging
from email.message import EmailMessage
from typing import TYPE_CHECKING, Any

import aiomqtt
import aiosmtplib
import httpx

from api.adapters.actions.formatting import event_payload, format_template
from api.adapters.http.client import client
from api.adapters.http.delivery_errors import http_delivery_error
from api.adapters.persistence.credentials import read_credential_payload
from api.application.errors import DeliveryError
from api.domain.credentials import (
    DiscordWebhookPayload,
    MqttPayload,
    SmtpPayload,
    TelegramBotPayload,
)

if TYPE_CHECKING:
    from api.application.execution import ExecutionIdentity
    from api.domain.events import DetectionEvent
    from api.domain.workflow import (
        DiscordActionData,
        EmailActionData,
        MqttActionData,
        TelegramActionData,
        WebhookActionData,
    )

logger = logging.getLogger(__name__)

DISCORD_CONTENT_LIMIT = 2000


async def run_webhook(
    identity: ExecutionIdentity,
    event: DetectionEvent,
    config: WebhookActionData,
    context: dict[str, Any],
) -> None:
    try:
        response = await client.request(
            config.method,
            config.url,
            json=event_payload(event, context),
            headers={"Idempotency-Key": str(context["delivery_id"])}
            if "delivery_id" in context
            else {},
            timeout=5,
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("webhook delivery failed node=%s", identity.node_id)
        raise http_delivery_error(exc) from None


async def run_telegram(
    identity: ExecutionIdentity,
    event: DetectionEvent,
    config: TelegramActionData,
    context: dict[str, Any],
) -> None:
    credential = await read_credential_payload(config.credential_id, TelegramBotPayload)
    if credential is None:
        logger.warning("telegram credential unavailable node=%s; skipping", identity.node_id)
        raise DeliveryError("telegram credential unavailable", retryable=False)

    message = format_template(config.message_template, event, context)
    # The URL embeds the bot token, so failures must not log it.
    base_url = f"https://api.telegram.org/bot{credential.bot_token}"
    snapshot: bytes | None = context.get("snapshot_jpeg")

    try:
        if snapshot is None:
            response = await client.post(
                f"{base_url}/sendMessage",
                json={"chat_id": config.chat_id, "text": message},
                timeout=10,
            )
        else:
            response = await client.post(
                f"{base_url}/sendPhoto",
                data={"chat_id": config.chat_id, "caption": message},
                files={"photo": ("snapshot.jpg", snapshot, "image/jpeg")},
                timeout=10,
            )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("telegram delivery failed chat=%s", config.chat_id)
        raise http_delivery_error(exc) from None


async def run_email(
    identity: ExecutionIdentity,
    event: DetectionEvent,
    config: EmailActionData,
    context: dict[str, Any],
) -> None:
    credential = await read_credential_payload(config.credential_id, SmtpPayload)
    if credential is None:
        logger.warning("smtp credential unavailable node=%s; skipping", identity.node_id)
        raise DeliveryError("smtp credential unavailable", retryable=False)

    message = EmailMessage()
    message["From"] = _email_sender(credential)
    message["To"] = _safe_header(config.to)
    message["Subject"] = _safe_header(format_template(config.subject_template, event, context))
    message.set_content(format_template(config.body_template, event, context))

    snapshot: bytes | None = context.get("snapshot_jpeg")
    if snapshot is not None:
        message.add_attachment(snapshot, maintype="image", subtype="jpeg", filename="snapshot.jpg")

    try:
        await aiosmtplib.send(
            message,
            hostname=credential.host,
            port=credential.port,
            username=credential.username,
            password=credential.password,
            start_tls=credential.starttls,
            timeout=10,
        )
    except (aiosmtplib.errors.SMTPException, OSError):
        logger.warning("email delivery failed to=%s", config.to)
        raise DeliveryError("SMTP delivery failed") from None


async def run_mqtt(
    identity: ExecutionIdentity,
    event: DetectionEvent,
    config: MqttActionData,
    context: dict[str, Any],
) -> None:
    credential = await read_credential_payload(config.credential_id, MqttPayload)
    if credential is None:
        logger.warning("mqtt credential unavailable node=%s; skipping", identity.node_id)
        raise DeliveryError("mqtt credential unavailable", retryable=False)

    if config.payload_template:
        payload = format_template(config.payload_template, event, context)
    else:
        payload = json.dumps(event_payload(event, context))

    try:
        async with aiomqtt.Client(
            hostname=credential.host,
            port=credential.port,
            username=credential.username,
            password=credential.password,
            timeout=5,
        ) as mqtt_client:
            await mqtt_client.publish(config.topic, payload)
    except aiomqtt.MqttError:
        logger.warning("mqtt publish failed topic=%s", config.topic)
        raise DeliveryError("MQTT delivery failed") from None


async def run_discord(
    identity: ExecutionIdentity,
    event: DetectionEvent,
    config: DiscordActionData,
    context: dict[str, Any],
) -> None:
    credential = await read_credential_payload(config.credential_id, DiscordWebhookPayload)
    if credential is None:
        logger.warning("discord credential unavailable node=%s; skipping", identity.node_id)
        raise DeliveryError("discord credential unavailable", retryable=False)

    message = format_template(config.message_template, event, context)
    if len(message) > DISCORD_CONTENT_LIMIT:
        logger.warning(
            "discord message truncated to %d chars workflow=%s",
            DISCORD_CONTENT_LIMIT,
            identity.workflow_id,
        )
        message = message[:DISCORD_CONTENT_LIMIT]

    # The webhook URL embeds its token, so failures must not log it.
    try:
        response = await client.post(
            str(credential.webhook_url), json={"content": message}, timeout=10
        )
        response.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("discord delivery failed workflow=%s", identity.workflow_id)
        raise http_delivery_error(exc) from None


def _email_sender(credential: SmtpPayload) -> str:
    if credential.from_address is not None:
        return credential.from_address

    if credential.username is not None:
        return credential.username

    return "looksee@localhost"


def _safe_header(value: str) -> str:
    return value.replace("\r", " ").replace("\n", " ")
