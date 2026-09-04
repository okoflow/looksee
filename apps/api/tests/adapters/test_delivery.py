"""External notification adapters against mocked transports and stubbed credentials."""

import json
from types import SimpleNamespace

import aiomqtt
import aiosmtplib
import httpx
import pytest

import api.adapters.actions.delivery as delivery
from api.application.errors import DeliveryError
from api.domain.credentials import (
    DiscordWebhookPayload,
    MqttPayload,
    SmtpPayload,
    TelegramBotPayload,
)
from api.domain.workflow import (
    DiscordActionData,
    EmailActionData,
    MqttActionData,
    TelegramActionData,
    WebhookActionData,
)

CREDENTIAL_ID = "5f1c6d4a-2d7e-4c1a-9b1e-3c2f1a0b9d8e"


@pytest.fixture
def credential(monkeypatch):
    holder = {"payload": None, "lookups": []}

    async def read(credential_id, payload_type):
        holder["lookups"].append((credential_id, payload_type))

        return holder["payload"]

    monkeypatch.setattr(delivery, "read_credential_payload", read)

    return holder


@pytest.fixture
async def transport(monkeypatch):
    requests = []
    responder = {"status": 200}

    def handler(request):
        requests.append(request)

        return httpx.Response(responder["status"], json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(delivery, "client", client)

    yield SimpleNamespace(requests=requests, responder=responder)

    await client.aclose()


async def test_webhook_sends_the_event_payload_with_the_configured_method(
    transport, identity, make_event
):
    event = make_event()
    config = WebhookActionData(url="https://hooks.example.com/looksee", method="PUT")

    await delivery.run_webhook(identity, event, config, {"snapshot_url": "/snapshots/a.jpg"})

    [request] = transport.requests

    assert request.method == "PUT"
    assert str(request.url) == "https://hooks.example.com/looksee"
    assert json.loads(request.content) == {
        "camera_id": str(event.camera_id),
        "kind": "PERSON_DETECTED",
        "ts": event.ts.isoformat(),
        "metadata": {"count": 1, "model_id": "people"},
        "snapshot_url": "/snapshots/a.jpg",
    }


async def test_webhook_failure_is_reported_safely(transport, identity, make_event, caplog):
    transport.responder["status"] = 502

    with pytest.raises(DeliveryError):
        await delivery.run_webhook(
            identity, make_event(), WebhookActionData(url="https://x.example"), {}
        )

    assert "webhook delivery failed node=" in caplog.text


async def test_telegram_without_credential_sends_nothing(
    transport, credential, identity, make_event, caplog
):
    config = TelegramActionData(credential_id=CREDENTIAL_ID, chat_id="42")

    with pytest.raises(DeliveryError):
        await delivery.run_telegram(identity, make_event(), config, {})

    assert credential["lookups"] == [(CREDENTIAL_ID, TelegramBotPayload)]
    assert transport.requests == []
    assert "telegram credential unavailable" in caplog.text


async def test_telegram_sends_a_formatted_message(transport, credential, identity, make_event):
    credential["payload"] = TelegramBotPayload(bot_token="123:secret-token")
    config = TelegramActionData(
        credential_id=CREDENTIAL_ID, chat_id="42", message_template="{kind} x{count}"
    )

    await delivery.run_telegram(identity, make_event(), config, {})

    [request] = transport.requests

    assert str(request.url) == "https://api.telegram.org/bot123:secret-token/sendMessage"
    assert json.loads(request.content) == {"chat_id": "42", "text": "PERSON_DETECTED x1"}


async def test_telegram_attaches_the_snapshot_as_a_photo(
    transport, credential, identity, make_event
):
    credential["payload"] = TelegramBotPayload(bot_token="123:secret-token")
    config = TelegramActionData(credential_id=CREDENTIAL_ID, chat_id="42")

    await delivery.run_telegram(identity, make_event(), config, {"snapshot_jpeg": b"jpeg-bytes"})

    [request] = transport.requests

    assert request.url.path.endswith("/sendPhoto")
    assert request.headers["content-type"].startswith("multipart/form-data")
    assert b'filename="snapshot.jpg"' in request.content
    assert b"jpeg-bytes" in request.content


async def test_telegram_failure_is_reported_safely(
    transport, credential, identity, make_event, caplog
):
    credential["payload"] = TelegramBotPayload(bot_token="123:secret-token")
    transport.responder["status"] = 401

    with pytest.raises(DeliveryError):
        await delivery.run_telegram(
            identity,
            make_event(),
            TelegramActionData(credential_id=CREDENTIAL_ID, chat_id="42"),
            {},
        )

    assert "telegram delivery failed chat=42" in caplog.text


async def test_telegram_failure_log_never_leaks_the_bot_token(
    transport, credential, identity, make_event, caplog
):
    credential["payload"] = TelegramBotPayload(bot_token="123:secret-token")
    transport.responder["status"] = 401

    with pytest.raises(DeliveryError):
        await delivery.run_telegram(
            identity,
            make_event(),
            TelegramActionData(credential_id=CREDENTIAL_ID, chat_id="42"),
            {},
        )

    assert "secret-token" not in caplog.text


async def test_discord_truncates_to_the_platform_limit(
    transport, credential, identity, make_event, caplog
):
    credential["payload"] = DiscordWebhookPayload(
        webhook_url="https://discord.com/api/webhooks/1/tok"
    )
    config = DiscordActionData(credential_id=CREDENTIAL_ID, message_template="x" * 1990 + "{kind}")

    await delivery.run_discord(identity, make_event(), config, {})

    [request] = transport.requests

    assert str(request.url) == "https://discord.com/api/webhooks/1/tok"
    assert json.loads(request.content) == {"content": "x" * 1990 + "PERSON_DET"}
    assert "discord message truncated to 2000 chars" in caplog.text


async def test_discord_failure_is_reported_safely(
    transport, credential, identity, make_event, caplog
):
    credential["payload"] = DiscordWebhookPayload(
        webhook_url="https://discord.com/api/webhooks/1/tok"
    )
    transport.responder["status"] = 500

    with pytest.raises(DeliveryError):
        await delivery.run_discord(
            identity, make_event(), DiscordActionData(credential_id=CREDENTIAL_ID), {}
        )

    assert "discord delivery failed" in caplog.text


async def test_discord_failure_log_never_leaks_the_webhook(
    transport, credential, identity, make_event, caplog
):
    credential["payload"] = DiscordWebhookPayload(
        webhook_url="https://discord.com/api/webhooks/1/tok"
    )
    transport.responder["status"] = 500

    with pytest.raises(DeliveryError):
        await delivery.run_discord(
            identity, make_event(), DiscordActionData(credential_id=CREDENTIAL_ID), {}
        )

    assert "webhooks/1/tok" not in caplog.text


class TestEmail:
    @pytest.fixture
    def smtp(self, monkeypatch):
        sent = []

        async def send(message, **kwargs):
            sent.append((message, kwargs))
            if kwargs["hostname"] == "down.example.com":
                raise aiosmtplib.errors.SMTPConnectError("refused")

        monkeypatch.setattr(delivery.aiosmtplib, "send", send)

        return sent

    async def test_email_is_built_from_credential_and_templates(
        self, smtp, credential, identity, make_event
    ):
        credential["payload"] = SmtpPayload(
            host="smtp.example.com",
            username="user",
            password="pw",
            from_address="alerts@example.com",
        )
        config = EmailActionData(
            credential_id=CREDENTIAL_ID,
            to="ops@example.com",
            subject_template="[{kind}]\r\nBcc: evil@example.com",
            body_template="camera {camera_id}",
        )
        event = make_event()

        await delivery.run_email(identity, event, config, {"snapshot_jpeg": b"jpeg"})

        [(message, kwargs)] = smtp

        assert message["From"] == "alerts@example.com"
        assert message["To"] == "ops@example.com"
        assert message["Subject"] == "[PERSON_DETECTED]  Bcc: evil@example.com"
        assert message.get_body().get_content().strip() == f"camera {event.camera_id}"
        assert [part.get_filename() for part in message.iter_attachments()] == ["snapshot.jpg"]
        assert kwargs == {
            "hostname": "smtp.example.com",
            "port": 587,
            "username": "user",
            "password": "pw",
            "start_tls": True,
            "timeout": 10,
        }

    @pytest.mark.parametrize(
        ("payload", "expected_from"),
        [
            (SmtpPayload(host="h", username="user@example.com"), "user@example.com"),
            (SmtpPayload(host="h"), "looksee@localhost"),
        ],
    )
    async def test_sender_falls_back_to_username_then_default(
        self, smtp, credential, identity, make_event, payload, expected_from
    ):
        credential["payload"] = payload

        await delivery.run_email(
            identity, make_event(), EmailActionData(credential_id=CREDENTIAL_ID, to="a@b"), {}
        )

        assert smtp[0][0]["From"] == expected_from
        assert list(smtp[0][0].iter_attachments()) == []

    async def test_smtp_failure_is_reported_safely(
        self, smtp, credential, identity, make_event, caplog
    ):
        credential["payload"] = SmtpPayload(host="down.example.com")

        with pytest.raises(DeliveryError):
            await delivery.run_email(
                identity, make_event(), EmailActionData(credential_id=CREDENTIAL_ID, to="a@b"), {}
            )

        assert "email delivery failed to=a@b" in caplog.text

    async def test_missing_credential_is_reported(
        self, smtp, credential, identity, make_event, caplog
    ):
        with pytest.raises(DeliveryError):
            await delivery.run_email(
                identity, make_event(), EmailActionData(credential_id=CREDENTIAL_ID, to="a@b"), {}
            )

        assert smtp == []
        assert "smtp credential unavailable" in caplog.text


class TestMqtt:
    @pytest.fixture
    def broker(self, monkeypatch):
        state = {"connections": [], "published": [], "fail": False}

        class FakeClient:
            def __init__(self, **kwargs):
                state["connections"].append(kwargs)

            async def __aenter__(self):
                if state["fail"]:
                    raise aiomqtt.MqttError("unreachable")

                return self

            async def __aexit__(self, *exc_info):
                return None

            async def publish(self, topic, payload):
                state["published"].append((topic, payload))

        monkeypatch.setattr(delivery.aiomqtt, "Client", FakeClient)

        return state

    async def test_default_payload_is_the_json_event(
        self, broker, credential, identity, make_event
    ):
        credential["payload"] = MqttPayload(host="broker.local", username="u", password="p")
        event = make_event()

        await delivery.run_mqtt(
            identity, event, MqttActionData(credential_id=CREDENTIAL_ID, topic="site/events"), {}
        )

        [(topic, payload)] = broker["published"]

        assert topic == "site/events"
        assert json.loads(payload)["camera_id"] == str(event.camera_id)
        assert broker["connections"] == [
            {
                "hostname": "broker.local",
                "port": 1883,
                "username": "u",
                "password": "p",
                "timeout": 5,
            }
        ]

    async def test_payload_template_overrides_the_json_document(
        self, broker, credential, identity, make_event
    ):
        credential["payload"] = MqttPayload(host="broker.local")
        config = MqttActionData(credential_id=CREDENTIAL_ID, payload_template="{kind}:{count}")

        await delivery.run_mqtt(identity, make_event(), config, {})

        assert broker["published"] == [("looksee/events", "PERSON_DETECTED:1")]

    async def test_broker_failure_is_reported_safely(
        self, broker, credential, identity, make_event, caplog
    ):
        credential["payload"] = MqttPayload(host="broker.local")
        broker["fail"] = True

        with pytest.raises(DeliveryError):
            await delivery.run_mqtt(
                identity, make_event(), MqttActionData(credential_id=CREDENTIAL_ID), {}
            )

        assert broker["published"] == []
        assert "mqtt publish failed topic=looksee/events" in caplog.text
