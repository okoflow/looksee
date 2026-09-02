"""Action payloads: defaults, credential requirements, runnable refinements."""

import typing
from uuid import UUID

import pytest
from pydantic import ValidationError

from api.domain.enums import AlertSeverity
from api.domain.workflow.actions import (
    ActionData,
    ActionNodeData,
    DiscordActionData,
    EmailActionData,
    LogAlertActionData,
    MqttActionData,
    RunnableDiscordAction,
    RunnableEmailAction,
    RunnableMqttAction,
    RunnableTelegramAction,
    RunnableWebhookAction,
    SnapshotActionData,
    TelegramActionData,
    WebhookActionData,
)

CREDENTIAL_ID = "8d1c9d4e-4b3e-4a5f-9c2d-1e2f3a4b5c6d"


@pytest.mark.parametrize(
    ("action_type", "kind", "credential_type"),
    [
        (TelegramActionData, "telegram_action", "telegram_bot"),
        (WebhookActionData, "webhook_action", None),
        (LogAlertActionData, "log_alert_action", None),
        (SnapshotActionData, "snapshot_action", None),
        (EmailActionData, "email_action", "smtp"),
        (MqttActionData, "mqtt_action", "mqtt"),
        (DiscordActionData, "discord_action", "discord_webhook"),
    ],
    ids=lambda value: value if isinstance(value, str) else "",
)
def test_each_action_declares_kind_and_credential_type(action_type, kind, credential_type):
    action = action_type()

    assert action.kind == kind
    assert action_type.credential_type == credential_type


def test_base_action_needs_no_credential():
    assert ActionNodeData.credential_type is None


def test_every_action_extends_the_base():
    for action_type in typing.get_args(ActionData):
        assert issubclass(action_type, ActionNodeData)


def test_credential_type_is_a_class_attribute_not_a_field():
    assert "credential_type" not in TelegramActionData.model_fields
    assert "credential_type" not in TelegramActionData().model_dump()


def test_telegram_defaults():
    action = TelegramActionData()

    assert action.credential_id == ""
    assert action.chat_id == ""
    assert action.message_template == "[{kind}] camera={camera_id} at {ts}"


def test_webhook_defaults():
    action = WebhookActionData()

    assert action.url == ""
    assert action.method == "POST"


def test_log_alert_defaults():
    action = LogAlertActionData()

    assert action.severity is AlertSeverity.WARNING
    assert action.cooldown_seconds == 30


def test_snapshot_defaults():
    action = SnapshotActionData()

    assert action.annotate is True


def test_email_defaults():
    action = EmailActionData()

    assert action.credential_id == ""
    assert action.to == ""
    assert action.subject_template == "[{kind}] on camera {camera_id}"
    assert action.body_template == "{kind} at {ts}\ncamera: {camera_id}\nsnapshot: {snapshot_url}"


def test_mqtt_defaults():
    action = MqttActionData()

    assert action.credential_id == ""
    assert action.topic == "looksee/events"
    assert action.payload_template == ""


def test_discord_defaults():
    action = DiscordActionData()

    assert action.credential_id == ""
    assert action.message_template == "[{kind}] camera={camera_id} at {ts}"


@pytest.mark.parametrize("method", ["POST", "GET", "PUT"])
def test_webhook_accepts_supported_methods(method):
    action = WebhookActionData(method=method)

    assert action.method == method


@pytest.mark.parametrize("severity", ["info", "warning", "critical"])
def test_log_alert_accepts_severity_values(severity):
    action = LogAlertActionData(severity=severity)

    assert action.severity is AlertSeverity(severity)


def test_log_alert_allows_zero_cooldown():
    action = LogAlertActionData(cooldown_seconds=0)

    assert action.cooldown_seconds == 0


@pytest.mark.parametrize(
    ("action_type", "fields"),
    [
        (TelegramActionData, {"credential_id": "x" * 37}),
        (TelegramActionData, {"chat_id": "x" * 65}),
        (TelegramActionData, {"message_template": "x" * 4097}),
        (WebhookActionData, {"method": "DELETE"}),
        (WebhookActionData, {"method": "post"}),
        (WebhookActionData, {"url": "x" * 2049}),
        (LogAlertActionData, {"severity": "fatal"}),
        (LogAlertActionData, {"cooldown_seconds": -1}),
        (LogAlertActionData, {"cooldown_seconds": 3601}),
        (SnapshotActionData, {"annotate": "sometimes"}),
        (SnapshotActionData, {"credential_id": "abc"}),
        (EmailActionData, {"to": "x" * 321}),
        (EmailActionData, {"subject_template": "x" * 999}),
        (EmailActionData, {"body_template": "x" * 8193}),
        (MqttActionData, {"topic": "x" * 513}),
        (MqttActionData, {"payload_template": "x" * 8193}),
        (DiscordActionData, {"message_template": "x" * 2001}),
        (DiscordActionData, {"kind": "telegram_action"}),
    ],
    ids=[
        "telegram_long_credential",
        "telegram_long_chat",
        "telegram_long_template",
        "webhook_unknown_method",
        "webhook_lowercase_method",
        "webhook_long_url",
        "alert_unknown_severity",
        "alert_negative_cooldown",
        "alert_long_cooldown",
        "snapshot_non_bool",
        "snapshot_unknown_field",
        "email_long_recipient",
        "email_long_subject",
        "email_long_body",
        "mqtt_long_topic",
        "mqtt_long_payload",
        "discord_long_template",
        "discord_foreign_kind",
    ],
)
def test_actions_reject_out_of_bound_fields(action_type, fields):
    with pytest.raises(ValidationError):
        action_type(**fields)


def test_runnable_telegram_requires_credential_and_chat():
    runnable = RunnableTelegramAction(credential_id=CREDENTIAL_ID, chat_id=" 42 ")

    assert runnable.credential_id == UUID(CREDENTIAL_ID)
    assert runnable.chat_id == "42"


@pytest.mark.parametrize(
    "fields",
    [
        {"chat_id": "42"},
        {"credential_id": "", "chat_id": "42"},
        {"credential_id": "not-a-uuid", "chat_id": "42"},
        {"credential_id": CREDENTIAL_ID},
        {"credential_id": CREDENTIAL_ID, "chat_id": ""},
        {"credential_id": CREDENTIAL_ID, "chat_id": "   "},
    ],
    ids=[
        "no_credential",
        "empty_credential",
        "malformed_credential",
        "no_chat",
        "empty_chat",
        "blank_chat",
    ],
)
def test_runnable_telegram_rejects_incomplete_config(fields):
    with pytest.raises(ValidationError):
        RunnableTelegramAction(**fields)


@pytest.mark.parametrize("url", ["https://hooks.example.com/x", "http://localhost:8080/hook"])
def test_runnable_webhook_accepts_http_urls(url):
    runnable = RunnableWebhookAction(url=url)

    assert str(runnable.url) == url


@pytest.mark.parametrize(
    "url", ["", "ftp://hooks.example.com/x", "hooks.example.com", "rtsp://cam/x"]
)
def test_runnable_webhook_rejects_non_http_urls(url):
    with pytest.raises(ValidationError, match="url"):
        RunnableWebhookAction(url=url)


def test_runnable_webhook_keeps_the_method():
    runnable = RunnableWebhookAction(url="https://hooks.example.com/x", method="PUT")

    assert runnable.method == "PUT"


def test_runnable_email_requires_credential_and_recipient():
    runnable = RunnableEmailAction(credential_id=CREDENTIAL_ID, to=" ops@example.com ")

    assert runnable.credential_id == UUID(CREDENTIAL_ID)
    assert runnable.to == "ops@example.com"


@pytest.mark.parametrize(
    "fields",
    [
        {"to": "ops@example.com"},
        {"credential_id": "", "to": "ops@example.com"},
        {"credential_id": CREDENTIAL_ID},
        {"credential_id": CREDENTIAL_ID, "to": ""},
        {"credential_id": CREDENTIAL_ID, "to": "   "},
    ],
    ids=["no_credential", "empty_credential", "no_recipient", "empty_recipient", "blank_recipient"],
)
def test_runnable_email_rejects_incomplete_config(fields):
    with pytest.raises(ValidationError):
        RunnableEmailAction(**fields)


def test_runnable_mqtt_requires_credential_and_topic():
    runnable = RunnableMqttAction(credential_id=CREDENTIAL_ID, topic=" site/a ")

    assert runnable.credential_id == UUID(CREDENTIAL_ID)
    assert runnable.topic == "site/a"


def test_runnable_mqtt_has_no_topic_default_of_its_own():
    with pytest.raises(ValidationError, match="topic"):
        RunnableMqttAction(credential_id=CREDENTIAL_ID)


def test_runnable_mqtt_accepts_the_draft_default_topic():
    draft = MqttActionData(credential_id=CREDENTIAL_ID)

    runnable = RunnableMqttAction.model_validate(draft.model_dump())

    assert runnable.topic == "looksee/events"


@pytest.mark.parametrize(
    "fields",
    [
        {},
        {"credential_id": "nope"},
        {"credential_id": CREDENTIAL_ID, "topic": ""},
        {"credential_id": CREDENTIAL_ID, "topic": " "},
    ],
    ids=["no_credential", "malformed_credential", "empty_topic", "blank_topic"],
)
def test_runnable_mqtt_rejects_incomplete_config(fields):
    with pytest.raises(ValidationError):
        RunnableMqttAction(**fields)


def test_runnable_discord_requires_a_credential():
    runnable = RunnableDiscordAction(credential_id=CREDENTIAL_ID)

    assert runnable.credential_id == UUID(CREDENTIAL_ID)


@pytest.mark.parametrize("credential_id", ["", "nope", "0" * 36])
def test_runnable_discord_rejects_non_uuid_credential(credential_id):
    with pytest.raises(ValidationError, match="credential_id"):
        RunnableDiscordAction(credential_id=credential_id)


def test_runnable_keeps_draft_templates():
    draft = TelegramActionData(
        credential_id=CREDENTIAL_ID, chat_id="42", message_template="hi {kind}"
    )

    runnable = RunnableTelegramAction.model_validate(draft.model_dump())

    assert runnable.message_template == "hi {kind}"


def test_runnable_actions_keep_their_credential_type():
    assert RunnableTelegramAction.credential_type == "telegram_bot"
    assert RunnableEmailAction.credential_type == "smtp"
    assert RunnableMqttAction.credential_type == "mqtt"
    assert RunnableDiscordAction.credential_type == "discord_webhook"
    assert RunnableWebhookAction.credential_type is None
