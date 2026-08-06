"""Auth transport contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str
    role: Literal["owner", "member"]
    created_at: datetime


class AuthStatusRead(BaseModel):
    requires_setup: bool


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class SetupRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=8, max_length=256)

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not any(character.isdigit() for character in value):
            raise ValueError("password must contain at least one number")

        if not any(character.isupper() for character in value):
            raise ValueError("password must contain at least one capital letter")

        return value
