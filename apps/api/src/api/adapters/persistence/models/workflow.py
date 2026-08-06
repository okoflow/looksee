from typing import TYPE_CHECKING, Any

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.adapters.persistence.db.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from api.adapters.persistence.models.camera import Camera


class Workflow(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "workflows"
    __table_args__ = (UniqueConstraint("name"),)

    name: Mapped[str]
    description: Mapped[str | None]
    enabled: Mapped[bool] = mapped_column(default=False, server_default="false")
    graph: Mapped[dict[str, Any]] = mapped_column(default=dict)

    cameras: Mapped[list["Camera"]] = relationship(
        lazy="raise",
        order_by="Camera.created_at",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
