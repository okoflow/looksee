"""Credential transport contracts; stored payloads are write-only."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from api.domain.credentials import CredentialType


class CredentialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    type: CredentialType
    summary: str
    created_at: datetime
    updated_at: datetime


class CredentialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    type: CredentialType
    payload: dict[str, Any]


class CredentialUpdate(BaseModel):
    """Partial update; omitting payload keeps the stored secret unchanged."""

    name: str | None = Field(default=None, min_length=1, max_length=128)
    payload: dict[str, Any] | None = None
