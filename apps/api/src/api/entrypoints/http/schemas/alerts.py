"""Alert HTTP response bodies."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from api.domain.enums import AlertSeverity


class AlertRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID | None
    camera_id: UUID | None
    kind: str
    severity: AlertSeverity
    message: str
    payload: dict[str, Any]
    created_at: datetime
