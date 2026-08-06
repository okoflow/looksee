"""Create the LookSee schema.

Revision ID: 0001
Revises:
Create Date: 2026-07-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision: str | None = None
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), server_default="owner", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.CheckConstraint("role IN ('owner', 'member')", name="user_role"),
    )

    op.create_table(
        "credentials",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=False),
        sa.Column("encrypted_payload", sa.String(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_credentials"),
        sa.UniqueConstraint("name", name="uq_credentials_name"),
        sa.CheckConstraint(
            "type IN ('telegram_bot', 'slack_webhook', 'discord_webhook', 'smtp', 'mqtt')",
            name="credential_type",
        ),
    )

    op.create_table(
        "workflows",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("graph", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_workflows"),
        sa.UniqueConstraint("name", name="uq_workflows_name"),
    )

    op.create_table(
        "cameras",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), nullable=False),
        sa.Column("node_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("source_type", sa.String(length=16), server_default="rtsp", nullable=False),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("runtime_revision", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("start_command", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(length=16), server_default="disabled", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_cameras"),
        sa.ForeignKeyConstraint(
            ["workflow_id"],
            ["workflows.id"],
            ondelete="CASCADE",
            name="fk_cameras_workflow_id_workflows",
        ),
        sa.UniqueConstraint("workflow_id", "node_id", name="uq_cameras_workflow_node"),
        sa.CheckConstraint("runtime_revision >= 0", name="runtime_revision"),
        sa.CheckConstraint(
            "source_type IN ('rtsp', 'rtmp', 'srt', 'webrtc', 'whep', 'file')",
            name="camera_source",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'active', 'error', 'disabled')",
            name="camera_status",
        ),
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), server_default=sa.text("uuidv7()"), nullable=False),
        sa.Column("workflow_id", sa.Uuid(), nullable=True),
        sa.Column("camera_id", sa.Uuid(), nullable=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_alerts"),
        sa.ForeignKeyConstraint(
            ["workflow_id"],
            ["workflows.id"],
            ondelete="SET NULL",
            name="fk_alerts_workflow_id_workflows",
        ),
        sa.ForeignKeyConstraint(
            ["camera_id"],
            ["cameras.id"],
            ondelete="SET NULL",
            name="fk_alerts_camera_id_cameras",
        ),
        sa.CheckConstraint(
            "severity IN ('info', 'warning', 'critical')",
            name="alert_severity",
        ),
    )
    op.create_index("ix_alerts_created_at", "alerts", ["created_at"])
    op.create_index("ix_alerts_camera_created", "alerts", ["camera_id", "created_at"])
    op.create_index("ix_alerts_workflow_created", "alerts", ["workflow_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_alerts_workflow_created", table_name="alerts")
    op.drop_index("ix_alerts_camera_created", table_name="alerts")
    op.drop_index("ix_alerts_created_at", table_name="alerts")
    op.drop_table("alerts")

    op.drop_table("cameras")

    op.drop_table("workflows")

    op.drop_table("credentials")

    op.drop_table("users")
