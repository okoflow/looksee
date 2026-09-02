"""Credential payload contracts and non-secret summaries."""

import pytest
from pydantic import ValidationError

from api.domain.credentials import (
    CREDENTIAL_PAYLOADS,
    CREDENTIAL_TYPE_BY_PAYLOAD,
    CREDENTIAL_TYPES,
    CredentialPayload,
    DiscordWebhookPayload,
    MqttPayload,
    SlackWebhookPayload,
    SmtpPayload,
    TelegramBotPayload,
    summarize_payload,
)


def test_registry_covers_every_credential_type_in_order():
    assert tuple(CREDENTIAL_PAYLOADS) == CREDENTIAL_TYPES


def test_payload_lookup_inverts_the_registry():
    for credential_type, payload_type in CREDENTIAL_PAYLOADS.items():
        assert CREDENTIAL_TYPE_BY_PAYLOAD[payload_type] == credential_type


def test_every_payload_type_extends_the_base():
    for payload_type in CREDENTIAL_PAYLOADS.values():
        assert issubclass(payload_type, CredentialPayload)


def test_telegram_token_is_stripped():
    payload = TelegramBotPayload(bot_token="  123:abc  ")

    assert payload.bot_token == "123:abc"


@pytest.mark.parametrize("token", ["", "   ", "x" * 257])
def test_telegram_rejects_blank_or_oversized_token(token):
    with pytest.raises(ValidationError):
        TelegramBotPayload(bot_token=token)


@pytest.mark.parametrize("payload_type", [SlackWebhookPayload, DiscordWebhookPayload])
def test_webhook_payloads_keep_https_url(payload_type):
    payload = payload_type(webhook_url="https://hooks.example.com/services/T/B/x")

    assert payload.webhook_url.scheme == "https"
    assert payload.webhook_url.host == "hooks.example.com"


@pytest.mark.parametrize("payload_type", [SlackWebhookPayload, DiscordWebhookPayload])
@pytest.mark.parametrize("url", ["ftp://hooks.example.com/x", "hooks.example.com", ""])
def test_webhook_payloads_require_http_url(payload_type, url):
    with pytest.raises(ValidationError):
        payload_type(webhook_url=url)


def test_smtp_defaults_to_submission_port_with_starttls():
    payload = SmtpPayload(host="smtp.example.com")

    assert payload.port == 587
    assert payload.starttls is True
    assert payload.username is None
    assert payload.password is None
    assert payload.from_address is None


def test_mqtt_defaults_to_plain_broker_port():
    payload = MqttPayload(host="broker.local")

    assert payload.port == 1883
    assert payload.username is None
    assert payload.password is None


@pytest.mark.parametrize("payload_type", [SmtpPayload, MqttPayload])
def test_host_is_stripped(payload_type):
    payload = payload_type(host="  broker.local ")

    assert payload.host == "broker.local"


@pytest.mark.parametrize("payload_type", [SmtpPayload, MqttPayload])
@pytest.mark.parametrize("port", [1, 65535])
def test_host_payloads_accept_port_boundaries(payload_type, port):
    payload = payload_type(host="example.com", port=port)

    assert payload.port == port


@pytest.mark.parametrize("payload_type", [SmtpPayload, MqttPayload])
@pytest.mark.parametrize("port", [0, 65536, -1])
def test_host_payloads_reject_out_of_range_port(payload_type, port):
    with pytest.raises(ValidationError):
        payload_type(host="example.com", port=port)


@pytest.mark.parametrize("payload_type", [SmtpPayload, MqttPayload])
@pytest.mark.parametrize("host", ["", "   ", "h" * 254])
def test_host_payloads_reject_blank_or_oversized_host(payload_type, host):
    with pytest.raises(ValidationError):
        payload_type(host=host)


def test_smtp_rejects_oversized_from_address():
    with pytest.raises(ValidationError):
        SmtpPayload(host="smtp.example.com", from_address="a" * 321)


@pytest.mark.parametrize(
    ("payload_type", "fields"),
    [
        (TelegramBotPayload, {"bot_token": "t"}),
        (SlackWebhookPayload, {"webhook_url": "https://hooks.slack.com/x"}),
        (DiscordWebhookPayload, {"webhook_url": "https://discord.com/api/webhooks/1/t"}),
        (SmtpPayload, {"host": "h"}),
        (MqttPayload, {"host": "h"}),
    ],
    ids=lambda value: getattr(value, "__name__", ""),
)
def test_payloads_reject_unknown_fields(payload_type, fields):
    with pytest.raises(ValidationError):
        payload_type(**fields, unexpected="x")


@pytest.mark.parametrize(
    ("payload_type", "fields"),
    [
        (TelegramBotPayload, {}),
        (SlackWebhookPayload, {}),
        (DiscordWebhookPayload, {}),
        (SmtpPayload, {"port": 25}),
        (MqttPayload, {"username": "u"}),
    ],
    ids=lambda value: getattr(value, "__name__", ""),
)
def test_payloads_require_their_primary_field(payload_type, fields):
    with pytest.raises(ValidationError):
        payload_type(**fields)


@pytest.mark.parametrize(
    ("credential_type", "payload", "expected"),
    [
        ("telegram_bot", TelegramBotPayload(bot_token="123:secret"), "Telegram bot"),
        (
            "slack_webhook",
            SlackWebhookPayload(webhook_url="https://hooks.slack.com/services/T/B/x"),
            "hooks.slack.com",
        ),
        (
            "discord_webhook",
            DiscordWebhookPayload(webhook_url="https://discord.com/api/webhooks/1/tok"),
            "discord.com",
        ),
        ("smtp", SmtpPayload(host="smtp.example.com"), "smtp.example.com:587"),
        ("mqtt", MqttPayload(host="broker.local", port=8883), "broker.local:8883"),
    ],
    ids=["telegram", "slack", "discord", "smtp", "mqtt"],
)
def test_summary_is_the_non_secret_hint(credential_type, payload, expected):
    assert summarize_payload(credential_type, payload) == expected


@pytest.mark.parametrize(
    ("credential_type", "payload"),
    [
        ("telegram_bot", TelegramBotPayload(bot_token="123:hunter2")),
        ("slack_webhook", SlackWebhookPayload(webhook_url="https://hooks.slack.com/T/hunter2")),
        ("discord_webhook", DiscordWebhookPayload(webhook_url="https://discord.com/api/hunter2")),
        ("smtp", SmtpPayload(host="smtp.example.com", username="bob", password="hunter2")),
        ("mqtt", MqttPayload(host="broker.local", username="bob", password="hunter2")),
    ],
    ids=["telegram", "slack", "discord", "smtp", "mqtt"],
)
def test_summary_never_leaks_secrets(credential_type, payload):
    summary = summarize_payload(credential_type, payload)

    assert "hunter2" not in summary
    assert "bob" not in summary


def test_summary_falls_back_to_the_type_for_unknown_payloads():
    class OpaquePayload(CredentialPayload):
        pass

    summary = summarize_payload("mqtt", OpaquePayload())

    assert summary == "mqtt"
