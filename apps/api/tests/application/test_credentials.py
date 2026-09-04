"""Credential use cases: validated, encrypted at rest, and resolved at enable time."""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from api.adapters.persistence.credentials import decrypt_payload
from api.adapters.persistence.models import Credential
from api.application import credentials
from api.application.errors import InvalidPayloadError, ResourceConflictError, ResourceNotFoundError
from api.domain.errors import GraphErrorCode, WorkflowGraphError
from api.domain.graph import WorkflowGraphIndex

CREDENTIAL_ID = "5f1c6d4a-2d7e-4c1a-9b1e-3c2f1a0b9d8e"


@pytest.mark.parametrize(
    ("credential_type", "payload", "summary"),
    [
        ("telegram_bot", {"bot_token": " 123:abc "}, "Telegram bot"),
        (
            "slack_webhook",
            {"webhook_url": "https://hooks.slack.com/services/T/B/x"},
            "hooks.slack.com",
        ),
        ("discord_webhook", {"webhook_url": "https://discord.com/api/webhooks/1/x"}, "discord.com"),
        ("smtp", {"host": "smtp.example.com"}, "smtp.example.com:587"),
        ("mqtt", {"host": "broker.local", "port": 8883}, "broker.local:8883"),
    ],
)
async def test_create_stores_summary_and_encrypted_payload(
    fake_session, credential_type, payload, summary
):
    credential = await credentials.create_credential(
        fake_session, name="main", credential_type=credential_type, payload=payload
    )

    stored = fake_session.rows[Credential][0]
    assert credential is stored
    assert stored.type == credential_type
    assert stored.summary == summary
    assert stored.encrypted_payload.startswith("gAAAA")
    for secret in payload.values():
        assert str(secret).strip() not in stored.encrypted_payload


async def test_encrypted_payload_decrypts_to_the_validated_document(fake_session):
    credential = await credentials.create_credential(
        fake_session, name="bot", credential_type="telegram_bot", payload={"bot_token": " tok "}
    )

    assert decrypt_payload(credential.encrypted_payload) == {"bot_token": "tok"}


@pytest.mark.parametrize(
    ("credential_type", "payload"),
    [
        ("telegram_bot", {}),
        ("telegram_bot", {"bot_token": "x", "chat_id": "1"}),
        ("slack_webhook", {"webhook_url": "not-a-url"}),
        ("smtp", {"host": "smtp.example.com", "port": 70000}),
        ("mqtt", {"host": ""}),
    ],
)
def test_invalid_payloads_are_rejected(credential_type, payload):
    with pytest.raises(InvalidPayloadError):
        credentials.validate_payload(credential_type, payload)


def test_validate_payload_applies_type_defaults():
    payload = credentials.validate_payload("mqtt", {"host": "broker"})

    assert payload.port == 1883
    assert payload.username is None


async def test_duplicate_name_reports_conflict_and_rolls_back(fake_session):
    await credentials.create_credential(
        fake_session, name="bot", credential_type="telegram_bot", payload={"bot_token": "a"}
    )

    with pytest.raises(ResourceConflictError, match="'bot' already exists"):
        await credentials.create_credential(
            fake_session, name="bot", credential_type="telegram_bot", payload={"bot_token": "b"}
        )

    assert len(fake_session.rows[Credential]) == 1
    assert fake_session.rollbacks == 1


async def test_unrelated_integrity_errors_propagate(fake_session, monkeypatch):
    async def failing_commit():
        raise IntegrityError("INSERT", {}, Exception("check violation"))

    monkeypatch.setattr(fake_session, "commit", failing_commit)

    with pytest.raises(IntegrityError):
        await credentials.create_credential(
            fake_session, name="bot", credential_type="telegram_bot", payload={"bot_token": "a"}
        )


async def test_update_rename_keeps_the_stored_secret(fake_session):
    credential = await credentials.create_credential(
        fake_session, name="bot", credential_type="telegram_bot", payload={"bot_token": "a"}
    )
    before = credential.encrypted_payload

    updated = await credentials.update_credential(
        fake_session, credential.id, name="renamed", payload=None
    )

    assert updated.name == "renamed"
    assert updated.encrypted_payload == before


async def test_update_payload_revalidates_against_the_existing_type(fake_session):
    credential = await credentials.create_credential(
        fake_session, name="mail", credential_type="smtp", payload={"host": "old.example.com"}
    )

    updated = await credentials.update_credential(
        fake_session, credential.id, name=None, payload={"host": "new.example.com", "port": 25}
    )

    assert updated.summary == "new.example.com:25"
    assert decrypt_payload(updated.encrypted_payload)["host"] == "new.example.com"
    with pytest.raises(InvalidPayloadError):
        await credentials.update_credential(
            fake_session, credential.id, name=None, payload={"bot_token": "wrong type"}
        )


async def test_update_and_delete_of_unknown_credential_raise_not_found(fake_session):
    with pytest.raises(ResourceNotFoundError, match="credential not found"):
        await credentials.update_credential(fake_session, uuid4(), name="x", payload=None)
    with pytest.raises(ResourceNotFoundError):
        await credentials.delete_credential(fake_session, uuid4())


async def test_delete_removes_the_row(fake_session):
    credential = await credentials.create_credential(
        fake_session, name="bot", credential_type="telegram_bot", payload={"bot_token": "a"}
    )

    await credentials.delete_credential(fake_session, credential.id)

    assert fake_session.rows[Credential] == []
    assert await credentials.list_credentials(fake_session) == []


async def test_list_returns_newest_first(fake_session):
    older = await credentials.create_credential(
        fake_session, name="older", credential_type="telegram_bot", payload={"bot_token": "a"}
    )
    newer = await credentials.create_credential(
        fake_session, name="newer", credential_type="telegram_bot", payload={"bot_token": "b"}
    )
    older.created_at = older.created_at.replace(year=2020)

    listed = await credentials.list_credentials(fake_session)

    assert listed == [newer, older]


class TestValidateCredentialsAvailable:
    def index(self, build_graph, basic_nodes, action):
        basic_nodes["act"] = action

        return WorkflowGraphIndex.build(build_graph(basic_nodes, [("cam", "det"), ("det", "act")]))

    async def test_actions_without_credentials_pass(self, fake_session, build_graph, basic_nodes):
        index = self.index(build_graph, basic_nodes, {"kind": "webhook_action", "url": "https://x"})

        await credentials.validate_credentials_available(fake_session, index)

    @pytest.mark.parametrize("credential_id", ["", "not-a-uuid", CREDENTIAL_ID])
    async def test_missing_credential_is_reported(
        self, fake_session, build_graph, basic_nodes, credential_id
    ):
        index = self.index(
            build_graph, basic_nodes, {"kind": "telegram_action", "credential_id": credential_id}
        )

        with pytest.raises(WorkflowGraphError) as excinfo:
            await credentials.validate_credentials_available(fake_session, index)

        assert excinfo.value.code is GraphErrorCode.CREDENTIAL_UNAVAILABLE
        assert excinfo.value.node_id == "act"

    async def test_credential_of_another_type_is_reported(
        self, fake_session, build_graph, basic_nodes
    ):
        credential = Credential(name="mail", type="smtp", summary="s", encrypted_payload="x")
        fake_session.seed(credential)
        index = self.index(
            build_graph,
            basic_nodes,
            {"kind": "telegram_action", "credential_id": str(credential.id), "chat_id": "1"},
        )

        with pytest.raises(WorkflowGraphError) as excinfo:
            await credentials.validate_credentials_available(fake_session, index)

        assert excinfo.value.code is GraphErrorCode.CREDENTIAL_TYPE_MISMATCH
        assert "'telegram_bot'" in str(excinfo.value)
        assert "'smtp'" in str(excinfo.value)

    async def test_matching_credential_passes(self, fake_session, build_graph, basic_nodes):
        credential = Credential(name="bot", type="telegram_bot", summary="s", encrypted_payload="x")
        fake_session.seed(credential)
        index = self.index(
            build_graph,
            basic_nodes,
            {"kind": "telegram_action", "credential_id": str(credential.id), "chat_id": "1"},
        )

        await credentials.validate_credentials_available(fake_session, index)
