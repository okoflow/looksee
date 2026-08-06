from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api.adapters.persistence.db.base import Base, TimestampMixin, UUIDMixin


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('owner', 'member')", name="user_role"),)

    email: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    password_hash: Mapped[str]
    role: Mapped[str] = mapped_column(default="owner", server_default="owner")
