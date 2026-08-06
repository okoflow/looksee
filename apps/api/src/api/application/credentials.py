"""Credential use cases: CRUD over encrypted payloads and the enable-time check.

Payloads are write-only: they are validated against their type's contract,
encrypted at rest, and never returned to clients. List views get a derived
non-secret summary instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from api.adapters.persistence.credentials import encrypt_payload
from api.adapters.persistence.models import Credential
from api.application.errors import ResourceConflictError, ResourceNotFoundError
from api.domain.credentials import (
    CREDENTIAL_PAYLOADS,
    CredentialType,
    summarize_payload,
)
from api.domain.errors import GraphErrorCode, WorkflowGraphError
from api.domain.workflow import ActionNodeData

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from api.domain.credentials import CredentialPayload
    from api.domain.graph import WorkflowGraphIndex

_NAME_CONSTRAINT = "uq_credentials_name"


def validate_payload(
    credential_type: CredentialType, payload: dict[str, object]
) -> CredentialPayload:
    return CREDENTIAL_PAYLOADS[credential_type].model_validate(payload)


async def list_credentials(session: AsyncSession) -> list[Credential]:
    result = await session.execute(select(Credential).order_by(Credential.created_at.desc()))

    return list(result.scalars().all())


async def get_credential(session: AsyncSession, credential_id: UUID) -> Credential:
    credential = await session.get(Credential, credential_id)
    if credential is None:
        raise ResourceNotFoundError("credential not found")

    return credential


async def create_credential(
    session: AsyncSession,
    *,
    name: str,
    credential_type: CredentialType,
    payload: dict[str, object],
) -> Credential:
    validated = validate_payload(credential_type, payload)
    credential = Credential(
        name=name,
        type=credential_type,
        summary=summarize_payload(credential_type, validated),
        encrypted_payload=encrypt_payload(validated),
    )
    session.add(credential)

    try:
        await session.commit()
    except IntegrityError as exc:
        await _translate_integrity_error(session, exc, name)

    await session.refresh(credential)

    return credential


async def update_credential(
    session: AsyncSession,
    credential_id: UUID,
    *,
    name: str | None,
    payload: dict[str, object] | None,
) -> Credential:
    credential = await get_credential(session, credential_id)

    if name is not None:
        credential.name = name

    if payload is not None:
        credential_type = cast("CredentialType", credential.type)
        validated = validate_payload(credential_type, payload)
        credential.summary = summarize_payload(credential_type, validated)
        credential.encrypted_payload = encrypt_payload(validated)

    credential_name = credential.name
    try:
        await session.commit()
    except IntegrityError as exc:
        await _translate_integrity_error(session, exc, credential_name)

    await session.refresh(credential)

    return credential


async def delete_credential(session: AsyncSession, credential_id: UUID) -> None:
    credential = await get_credential(session, credential_id)
    await session.delete(credential)
    await session.commit()


async def validate_credentials_available(session: AsyncSession, index: WorkflowGraphIndex) -> None:
    """Every action that references a credential must resolve to one of its type."""
    for node_id in sorted(index.nodes_by_id):
        data = index.nodes_by_id[node_id]
        if not isinstance(data, ActionNodeData) or data.credential_type is None:
            continue

        credential = await _find_credential(session, getattr(data, "credential_id", ""))
        if credential is None:
            raise WorkflowGraphError(GraphErrorCode.CREDENTIAL_UNAVAILABLE, node_id=node_id)

        if credential.type != data.credential_type:
            raise WorkflowGraphError(
                GraphErrorCode.CREDENTIAL_TYPE_MISMATCH,
                node_id=node_id,
                expected=data.credential_type,
                actual=credential.type,
            )


async def _find_credential(session: AsyncSession, credential_id: str) -> Credential | None:
    try:
        parsed_id = UUID(credential_id)
    except ValueError:
        return None

    return await session.get(Credential, parsed_id)


async def _translate_integrity_error(
    session: AsyncSession,
    exc: IntegrityError,
    name: str,
) -> None:
    await session.rollback()
    if not _is_name_conflict(exc):
        raise exc
    raise ResourceConflictError(f"Credential named '{name}' already exists") from None


def _is_name_conflict(exc: IntegrityError) -> bool:
    cause: BaseException | None = exc.orig
    while cause is not None:
        if getattr(cause, "constraint_name", None) == _NAME_CONSTRAINT:
            return True
        cause = cause.__cause__

    return False
