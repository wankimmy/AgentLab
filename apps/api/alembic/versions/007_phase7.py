"""Phase 7: LLM judge, human review, blind A/B."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "007_phase7"
down_revision: str | None = "006_phase6"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    judge_source = postgresql.ENUM(
        "message", "evaluation_result", "multi", name="judgesourcetype", create_type=True
    )
    judge_run_status = postgresql.ENUM(
        "pending", "running", "completed", "failed", name="judgerunstatus", create_type=True
    )
    human_verdict = postgresql.ENUM(
        "pass", "fail", "needs_review", name="humanreviewverdict", create_type=True
    )

    op.create_table(
        "judge_rubric_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("criteria", postgresql.JSONB(), server_default="{}"),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("is_system", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "judge_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "rubric_template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("judge_rubric_templates.id"),
        ),
        sa.Column("source_type", judge_source, nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(50), server_default="mock"),
        sa.Column("model", sa.String(100), server_default=""),
        sa.Column("status", judge_run_status, server_default="pending"),
        sa.Column("input_tokens", sa.Integer(), server_default="0"),
        sa.Column("output_tokens", sa.Integer(), server_default="0"),
        sa.Column("estimated_cost", sa.Numeric(12, 6), server_default="0"),
        sa.Column("config_snapshot", postgresql.JSONB(), server_default="{}"),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_judge_runs_source", "judge_runs", ["source_type", "source_id"])

    op.create_table(
        "judge_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "judge_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("judge_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "evaluation_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_results.id"),
        ),
        sa.Column("criteria_scores", postgresql.JSONB(), server_default="{}"),
        sa.Column("overall_score", sa.Numeric(5, 2)),
        sa.Column("passed", sa.Boolean(), server_default="false"),
        sa.Column("explanation", sa.Text()),
        sa.Column("evidence", postgresql.ARRAY(sa.Text()), server_default="{}"),
        sa.Column("structured_raw", postgresql.JSONB(), server_default="{}"),
        sa.Column("judge_index", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "human_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "evaluation_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_results.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "reviewer_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("verdict", human_verdict, nullable=False),
        sa.Column("rating", sa.Integer()),
        sa.Column("notes", sa.Text()),
        sa.Column("issue_category", sa.String(100)),
        sa.Column("suggested_improvement", sa.Text()),
        sa.Column("preferred_answer", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "blind_ab_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "reviewer_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "left_message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("messages.id"),
            nullable=False,
        ),
        sa.Column(
            "right_message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("messages.id"),
            nullable=False,
        ),
        sa.Column("left_label", sa.String(255), nullable=False),
        sa.Column("right_label", sa.String(255), nullable=False),
        sa.Column("preference", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("blind_ab_reviews")
    op.drop_table("human_reviews")
    op.drop_table("judge_results")
    op.drop_index("ix_judge_runs_source", table_name="judge_runs")
    op.drop_table("judge_runs")
    op.drop_table("judge_rubric_templates")
    sa.Enum(name="humanreviewverdict").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="judgerunstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="judgesourcetype").drop(op.get_bind(), checkfirst=True)
