"""Decrypted credential reads for delivery adapters."""

from uuid import uuid4

import pytest
from cryptography.fernet import InvalidToken

from api.adapters.persistence.credentials import (
    decrypt_payload,
    encrypt_payload,
    read_credential_payload,
)
from api.adapters.persistence.models import Credential
from api.domain.credentials import SmtpPayload, TelegramBotPayload


def test_encrypt_hides_the_secret_and_decrypt_restores_the_document():
    payload = TelegramBotPayload(bot_token="123:secret")

    encrypted = encrypt_payload(payload)

    assert "secret" not in encrypted
    assert decrypt_payload(encrypted) == {"bot_token": "123:secret"}


def test_tampered_ciphertext_is_rejected():
    encrypted = encrypt_payload(TelegramBotPayload(bot_token="123:secret"))

    with pytest.raises(InvalidToken):
        decrypt_payload(encrypted[:-4] + "AAAA")


@pytest.fixture
def stored(effects, fake_session):
    credential = Credential(
        name="bot",
        type="telegram_bot",
        summary="Telegram bot",
        encrypted_payload=encrypt_payload(TelegramBotPayload(bot_token="123:secret")),
    )
    fake_session.seed(credential)

    return credential


async def test_read_returns_the_typed_payload(stored):
    payload = await read_credential_payload(str(stored.id), TelegramBotPayload)

    assert payload == TelegramBotPayload(bot_token="123:secret")


async def test_read_of_malformed_id_is_none(stored, caplog):
    assert await read_credential_payload("nope", TelegramBotPayload) is None
    assert "invalid credential id 'nope'" in caplog.text


async def test_read_of_unknown_credential_is_none(stored, caplog):
    missing = uuid4()

    assert await read_credential_payload(str(missing), TelegramBotPayload) is None
    assert f"credential {missing} not found" in caplog.text


async def test_read_with_another_payload_type_is_none(stored, caplog):
    assert await read_credential_payload(str(stored.id), SmtpPayload) is None
    assert "has type telegram_bot, expected smtp" in caplog.text


async def test_read_of_corrupt_ciphertext_is_none(stored, caplog):
    stored.encrypted_payload = "garbage"

    assert await read_credential_payload(str(stored.id), TelegramBotPayload) is None
    assert "failed to decrypt or validate" in caplog.text
