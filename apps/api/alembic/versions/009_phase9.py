"""Phase 9: prompt recommendations, red team, comparison AI summary."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "009_phase9"
down_revision: str | None = "008_phase8"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    rec_source = postgresql.ENUM(
        "analyse", "failed_cases", name="promptrecommendationsource", create_type=True
    )
    rec_status = postgresql.ENUM(
        "draft", "accepted", "dismissed", name="promptrecommendationstatus", create_type=True
    )
    rt_status = postgresql.ENUM(
        "pending", "running", "completed", "failed", name="redteamrunstatus", create_type=True
    )

    op.create_table(
        "prompt_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_versions.id"),
            nullable=False,
        ),
        sa.Column("source", rec_source, nullable=False),
        sa.Column("suggestions", postgresql.JSONB(), server_default="[]"),
        sa.Column("status", rec_status, server_default="draft"),
        sa.Column("estimated_cost", sa.Numeric(12, 6)),
        sa.Column(
            "created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "red_team_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "agent_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_versions.id"),
            nullable=False,
        ),
        sa.Column("status", rt_status, server_default="pending"),
        sa.Column("categories", postgresql.JSONB(), server_default="[]"),
        sa.Column("config_snapshot", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "red_team_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "red_team_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("red_team_runs.id"),
            nullable=False,
        ),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("response", sa.Text(), server_default=""),
        sa.Column("passed", sa.Boolean()),
        sa.Column("severity", sa.String(20), server_default="medium"),
        sa.Column(
            "promoted_case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_cases.id"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.add_column("comparison_runs", sa.Column("ai_summary", sa.Text()))
    op.add_column(
        "comparison_runs",
        sa.Column("ai_summary_status", sa.String(30), server_default="pending"),
    )


def downgrade() -> None:
    op.drop_column("comparison_runs", "ai_summary_status")
    op.drop_column("comparison_runs", "ai_summary")
    op.drop_table("red_team_cases")
    op.drop_table("red_team_runs")
    op.drop_table("prompt_recommendations")
    sa.Enum(name="redteamrunstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="promptrecommendationstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="promptrecommendationsource").drop(op.get_bind(), checkfirst=True)
