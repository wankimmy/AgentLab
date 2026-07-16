"""Phase 5: tool approvals and audit logs."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "005_phase5"
down_revision: str | None = "004_phase4"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    approval_status = postgresql.ENUM(
        "pending",
        "approved",
        "rejected",
        "expired",
        name="toolapprovalstatus",
        create_type=True,
    )

    op.create_table(
        "tool_approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column("message_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("messages.id")),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_traces.id")),
        sa.Column("tool_name", sa.String(100), nullable=False),
        sa.Column("tool_call_id", sa.String(100), nullable=False),
        sa.Column("arguments", postgresql.JSONB(), server_default="{}"),
        sa.Column("status", approval_status, server_default="pending"),
        sa.Column("decided_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_tool_approvals_status_created",
        "tool_approvals",
        ["status", "created_at"],
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=False),
        sa.Column("details", postgresql.JSONB(), server_default="{}"),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_traces.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_audit_logs_user_created",
        "audit_logs",
        ["user_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("tool_approvals")
    op.execute("DROP TYPE IF EXISTS toolapprovalstatus")
