"""Persist delivery attempts independently of frame consumption."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deliveries",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("deduplication_key", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(), server_default="pending", nullable=False),
        sa.Column("attempts", sa.Integer(), server_default="0", nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_id", sa.Uuid(), nullable=True),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.PrimaryKeyConstraint("id", name="pk_deliveries"),
        sa.UniqueConstraint("deduplication_key", name="uq_deliveries_deduplication_key"),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'sent', 'failed')", name="delivery_status"
        ),
        sa.CheckConstraint("attempts >= 0", name="delivery_attempts"),
    )
    op.create_index("ix_deliveries_status_available", "deliveries", ["status", "available_at"])


def downgrade() -> None:
    op.drop_index("ix_deliveries_status_available", table_name="deliveries")
    op.drop_table("deliveries")
