from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api.adapters.persistence.db.base import Base, TimestampMixin, UUIDMixin
from api.domain.credentials import CREDENTIAL_TYPES


class Credential(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "credentials"
    __table_args__ = (
        CheckConstraint(
            "type IN ({})".format(", ".join(f"'{name}'" for name in CREDENTIAL_TYPES)),
            name="credential_type",
        ),
    )

    name: Mapped[str] = mapped_column(unique=True)
    type: Mapped[str] = mapped_column()
    # Non-secret hint for list views (host or service name), derived on write.
    summary: Mapped[str]
    encrypted_payload: Mapped[str]
