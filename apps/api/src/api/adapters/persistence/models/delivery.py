from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column

from api.adapters.persistence.db.base import Base, TimestampMixin, UUIDMixin


class Delivery(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "deliveries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'processing', 'sent', 'failed')", name="delivery_status"
        ),
        CheckConstraint("attempts >= 0", name="delivery_attempts"),
        Index("ix_deliveries_status_available", "status", "available_at"),
    )

    deduplication_key: Mapped[str] = mapped_column(unique=True)
    payload: Mapped[dict[str, Any]]
    status: Mapped[str] = mapped_column(default="pending", server_default="pending")
    attempts: Mapped[int] = mapped_column(default=0, server_default="0")
    available_at: Mapped[datetime]
    lease_id: Mapped[UUID | None]
    lease_until: Mapped[datetime | None]
    last_error: Mapped[str | None]
