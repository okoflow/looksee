"""Decrypted credential reads for delivery adapters.

Payloads are resolved at delivery time, so editing a credential applies to
every enabled workflow without re-saving them.
"""

import json
import logging
from uuid import UUID

from pydantic import ValidationError

from api.adapters.persistence.db import session_factory
from api.adapters.persistence.models import Credential
from api.adapters.security import credentials_fernet
from api.domain.credentials import CREDENTIAL_TYPE_BY_PAYLOAD, CredentialPayload

logger = logging.getLogger(__name__)


def encrypt_payload(payload: CredentialPayload) -> str:
    serialized = payload.model_dump_json().encode()

    return credentials_fernet().encrypt(serialized).decode()


def decrypt_payload(encrypted_payload: str) -> dict[str, object]:
    decrypted = credentials_fernet().decrypt(encrypted_payload.encode())
    payload: dict[str, object] = json.loads(decrypted)

    return payload


async def read_credential_payload[PayloadT: CredentialPayload](
    credential_id: str,
    payload_type: type[PayloadT],
) -> PayloadT | None:
    """Load and decrypt one credential; None when missing, mistyped, or corrupt."""
    expected_type = CREDENTIAL_TYPE_BY_PAYLOAD[payload_type]

    try:
        parsed_id = UUID(credential_id)
    except ValueError:
        logger.warning("invalid credential id %r", credential_id)
        return None

    async with session_factory() as session:
        credential = await session.get(Credential, parsed_id)

    if credential is None:
        logger.warning("credential %s not found", credential_id)
        return None

    if credential.type != expected_type:
        logger.warning(
            "credential %s has type %s, expected %s",
            credential_id,
            credential.type,
            expected_type,
        )
        return None

    try:
        return payload_type.model_validate(decrypt_payload(credential.encrypted_payload))
    except (ValidationError, ValueError):
        logger.exception("credential %s payload failed to decrypt or validate", credential_id)
        return None
