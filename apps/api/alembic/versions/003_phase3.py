"""Phase 3: playground conversations, traces, model registry."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "003_phase3"
down_revision: str | None = "002_phase2"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    message_role = postgresql.ENUM(
        "system", "user", "assistant", "tool", name="messagerole", create_type=True
    )

    op.create_table(
        "model_registry",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("context_limit", sa.Integer(), server_default="8192"),
        sa.Column("streaming", sa.Boolean(), server_default="true"),
        sa.Column("tool_calling", sa.Boolean(), server_default="false"),
        sa.Column("structured_output", sa.Boolean(), server_default="false"),
        sa.Column("active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("provider", "model", name="uq_model_registry"),
    )

    op.create_table(
        "model_pricing",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("input_token_cost", sa.Numeric(12, 8), server_default="0"),
        sa.Column("output_token_cost", sa.Numeric(12, 8), server_default="0"),
        sa.Column("effective_from", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False
        ),
        sa.Column(
            "agent_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_versions.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), server_default="New conversation"),
        sa.Column("memory_summary", sa.Text(), nullable=True),
        sa.Column("memory_summary_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("conversations.id"),
            nullable=False,
        ),
        sa.Column("role", message_role, nullable=False),
        sa.Column("content", sa.Text(), server_default=""),
        sa.Column("tool_calls", postgresql.JSONB(), nullable=True),
        sa.Column("tool_call_id", sa.String(100), nullable=True),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("conversation_id", "sequence", name="uq_message_sequence"),
    )

    op.create_table(
        "chat_traces",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("messages.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "agent_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_versions.id"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(100), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("runtime", sa.String(50), server_default="native"),
        sa.Column("duration_ms", sa.Integer(), server_default="0"),
        sa.Column("ttft_ms", sa.Integer(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), server_default="0"),
        sa.Column("output_tokens", sa.Integer(), server_default="0"),
        sa.Column("estimated_cost", sa.Numeric(12, 8), server_default="0"),
        sa.Column("retrieved_chunks", postgresql.JSONB(), server_default="[]"),
        sa.Column("tool_requests", postgresql.JSONB(), server_default="[]"),
        sa.Column("tool_results", postgresql.JSONB(), server_default="[]"),
        sa.Column("guardrail_results", postgresql.JSONB(), server_default="[]"),
        sa.Column("overrides", postgresql.JSONB(), server_default="{}"),
        sa.Column("errors", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "trace_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "trace_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_traces.id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload", postgresql.JSONB(), server_default="{}"),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "message_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("messages.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("message_feedback")
    op.drop_table("trace_events")
    op.drop_table("chat_traces")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("model_pricing")
    op.drop_table("model_registry")
    op.execute("DROP TYPE IF EXISTS messagerole")
