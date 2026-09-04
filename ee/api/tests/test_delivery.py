"""Slack webhook delivery with stubbed credentials and a mocked transport."""

import json
from types import SimpleNamespace

import httpx
import pytest

from api.application.errors import DeliveryError
from api.domain.credentials import SlackWebhookPayload
from ee.adapters import delivery
from ee.workflow.actions import SlackActionData

CREDENTIAL_ID = "5f1c6d4a-2d7e-4c1a-9b1e-3c2f1a0b9d8e"
WEBHOOK = "https://hooks.slack.com/services/T000/B000/secret-token"


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

        return httpx.Response(responder["status"], text="ok")

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    monkeypatch.setattr(delivery, "client", client)

    yield SimpleNamespace(requests=requests, responder=responder)

    await client.aclose()


async def test_missing_credential_is_reported(transport, credential, identity, make_event, caplog):
    with pytest.raises(DeliveryError):
        await delivery.run_slack(
            identity, make_event(), SlackActionData(credential_id=CREDENTIAL_ID), {}
        )

    assert credential["lookups"] == [(CREDENTIAL_ID, SlackWebhookPayload)]
    assert transport.requests == []
    assert "slack credential unavailable node=slack" in caplog.text


async def test_message_is_posted_to_the_webhook(transport, credential, identity, make_event):
    credential["payload"] = SlackWebhookPayload(webhook_url=WEBHOOK)
    config = SlackActionData(
        credential_id=CREDENTIAL_ID, message_template="{kind} at {ts} {snapshot_url}"
    )
    event = make_event()

    await delivery.run_slack(identity, event, config, {"snapshot_url": "/snapshots/a.jpg"})

    [request] = transport.requests

    assert request.method == "POST"
    assert str(request.url) == WEBHOOK
    assert json.loads(request.content) == {
        "text": f"PERSON_DETECTED at {event.ts.isoformat()} /snapshots/a.jpg"
    }


async def test_failure_is_reported_safely(transport, credential, identity, make_event, caplog):
    credential["payload"] = SlackWebhookPayload(webhook_url=WEBHOOK)
    transport.responder["status"] = 403

    with pytest.raises(DeliveryError):
        await delivery.run_slack(
            identity, make_event(), SlackActionData(credential_id=CREDENTIAL_ID), {}
        )

    assert f"slack delivery failed workflow={identity.workflow_id}" in caplog.text


async def test_failure_log_never_leaks_the_webhook(
    transport, credential, identity, make_event, caplog
):
    credential["payload"] = SlackWebhookPayload(webhook_url=WEBHOOK)
    transport.responder["status"] = 403

    with pytest.raises(DeliveryError):
        await delivery.run_slack(
            identity, make_event(), SlackActionData(credential_id=CREDENTIAL_ID), {}
        )

    assert "secret-token" not in caplog.text
