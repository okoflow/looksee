from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column

from api.adapters.persistence.db.base import Base, TimestampMixin, UUIDMixin
from api.adapters.persistence.db.types import string_enum
from api.domain.enums import AlertSeverity


class Alert(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_created_at", "created_at"),
        Index("ix_alerts_camera_created", "camera_id", "created_at"),
        Index("ix_alerts_workflow_created", "workflow_id", "created_at"),
    )

    workflow_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("workflows.id", ondelete="SET NULL")
    )
    camera_id: Mapped[UUID | None] = mapped_column(ForeignKey("cameras.id", ondelete="SET NULL"))
    kind: Mapped[str]
    severity: Mapped[AlertSeverity] = mapped_column(
        string_enum(AlertSeverity, "alert_severity"),
        default=AlertSeverity.WARNING,
    )
    message: Mapped[str]
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)
