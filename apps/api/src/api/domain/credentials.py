"""Credential type vocabulary and per-type secret payload contracts.

A credential is a named, encrypted payload referenced by action nodes through
`credential_id`. Payloads are validated against the strict models below on
create and on decrypt; the API never returns a stored payload back to clients.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints

CredentialType = Literal[
    "telegram_bot",
    "slack_webhook",
    "discord_webhook",
    "smtp",
    "mqtt",
]

CREDENTIAL_TYPES: tuple[CredentialType, ...] = (
    "telegram_bot",
    "slack_webhook",
    "discord_webhook",
    "smtp",
    "mqtt",
)

Host = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=253)]
Port = Annotated[int, Field(ge=1, le=65535)]


class CredentialPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TelegramBotPayload(CredentialPayload):
    bot_token: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)
    ]


class SlackWebhookPayload(CredentialPayload):
    webhook_url: HttpUrl


class DiscordWebhookPayload(CredentialPayload):
    webhook_url: HttpUrl


class SmtpPayload(CredentialPayload):
    host: Host
    port: Port = 587
    username: str | None = None
    password: str | None = None
    from_address: str | None = Field(default=None, max_length=320)
    starttls: bool = True


class MqttPayload(CredentialPayload):
    host: Host
    port: Port = 1883
    username: str | None = None
    password: str | None = None


CREDENTIAL_PAYLOADS: dict[CredentialType, type[CredentialPayload]] = {
    "telegram_bot": TelegramBotPayload,
    "slack_webhook": SlackWebhookPayload,
    "discord_webhook": DiscordWebhookPayload,
    "smtp": SmtpPayload,
    "mqtt": MqttPayload,
}

CREDENTIAL_TYPE_BY_PAYLOAD: dict[type[CredentialPayload], CredentialType] = {
    payload_type: credential_type for credential_type, payload_type in CREDENTIAL_PAYLOADS.items()
}


def summarize_payload(credential_type: CredentialType, payload: CredentialPayload) -> str:
    """Build the non-secret list-view hint stored next to the encrypted payload."""
    if isinstance(payload, TelegramBotPayload):
        return "Telegram bot"

    if isinstance(payload, SlackWebhookPayload | DiscordWebhookPayload):
        host = payload.webhook_url.host
        return host if host is not None else credential_type

    if isinstance(payload, SmtpPayload | MqttPayload):
        return f"{payload.host}:{payload.port}"

    return credential_type
