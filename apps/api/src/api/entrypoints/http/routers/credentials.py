"""Credential HTTP entrypoints; payloads go in encrypted and never come back."""

from uuid import UUID

from fastapi import APIRouter, Depends, status

from api.adapters.persistence.models import Credential
from api.application import credentials
from api.entrypoints.http.dependencies import SessionDep, get_current_user
from api.entrypoints.http.schemas.credentials import (
    CredentialCreate,
    CredentialRead,
    CredentialUpdate,
)

router = APIRouter(
    prefix="/credentials",
    tags=["credentials"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[CredentialRead])
async def list_credentials(session: SessionDep) -> list[Credential]:
    return await credentials.list_credentials(session)


@router.post("", response_model=CredentialRead, status_code=status.HTTP_201_CREATED)
async def create_credential(payload: CredentialCreate, session: SessionDep) -> Credential:
    return await credentials.create_credential(
        session,
        name=payload.name,
        credential_type=payload.type,
        payload=payload.payload,
    )


@router.patch("/{credential_id}", response_model=CredentialRead)
async def update_credential(
    credential_id: UUID,
    payload: CredentialUpdate,
    session: SessionDep,
) -> Credential:
    return await credentials.update_credential(
        session,
        credential_id,
        name=payload.name,
        payload=payload.payload,
    )


@router.delete("/{credential_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_credential(credential_id: UUID, session: SessionDep) -> None:
    await credentials.delete_credential(session, credential_id)
