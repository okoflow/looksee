from typing import Any
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api.adapters.persistence.db.base import Base, TimestampMixin, UUIDMixin
from api.adapters.persistence.db.types import string_enum
from api.domain.enums import CameraSource, CameraStatus


class Camera(Base, UUIDMixin, TimestampMixin):
    """Runtime state of one `camera_source` node — derived from the workflow graph on save."""

    __tablename__ = "cameras"
    __table_args__ = (
        CheckConstraint("runtime_revision >= 0", name="runtime_revision"),
        UniqueConstraint("workflow_id", "node_id", name="uq_cameras_workflow_node"),
    )

    workflow_id: Mapped[UUID] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"))
    node_id: Mapped[str]
    name: Mapped[str]
    source_type: Mapped[CameraSource] = mapped_column(
        string_enum(CameraSource, "camera_source"),
        default=CameraSource.RTSP,
        server_default=CameraSource.RTSP.value,
    )
    source_url: Mapped[str | None]
    runtime_revision: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    start_command: Mapped[dict[str, Any] | None]
    status: Mapped[CameraStatus] = mapped_column(
        string_enum(CameraStatus, "camera_status"),
        default=CameraStatus.DISABLED,
        server_default=CameraStatus.DISABLED.value,
    )
