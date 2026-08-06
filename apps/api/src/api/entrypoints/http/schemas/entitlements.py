"""Entitlements HTTP response body."""

from pydantic import BaseModel

from api.application.entitlements import Edition


class EntitlementsRead(BaseModel):
    edition: Edition
    features: list[str]
