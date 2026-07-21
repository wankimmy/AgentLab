"""Phase 8: comparison, regression, release thresholds, release checks."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "008_phase8"
down_revision: str | None = "007_phase7"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    comparison_status = postgresql.ENUM(
        "pending", "running", "completed", "failed", name="comparisonrunstatus", create_type=True
    )
    case_classification = postgresql.ENUM(
        "improved", "regressed", "unchanged", name="caseclassification", create_type=True
    )
    release_check_status = postgresql.ENUM(
        "passed", "failed", "blocked", name="releasecheckstatus", create_type=True
    )

    op.create_table(
        "release_threshold_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("rules", postgresql.JSONB(), server_default="{}"),
        sa.Column("version", sa.Integer(), server_default="1"),
        sa.Column("is_system", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "comparison_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column(
            "baseline_agent_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "candidate_agent_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "baseline_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_runs.id"),
        ),
        sa.Column(
            "candidate_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_runs.id"),
        ),
        sa.Column("status", comparison_status, server_default="pending"),
        sa.Column("baseline_pass_rate", sa.Numeric(5, 4)),
        sa.Column("candidate_pass_rate", sa.Numeric(5, 4)),
        sa.Column("pass_rate_delta", sa.Numeric(6, 4)),
        sa.Column("config_snapshot", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "regression_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "comparison_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("comparison_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_cases.id"),
        ),
        sa.Column("case_name", sa.String(255), server_default=""),
        sa.Column("classification", case_classification, nullable=False),
        sa.Column("severity", sa.String(20), server_default="medium"),
        sa.Column("details", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_regression_results_comparison", "regression_results", ["comparison_run_id"])

    op.create_table(
        "release_checks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "eval_run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_runs.id"),
        ),
        sa.Column(
            "threshold_template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("release_threshold_templates.id"),
        ),
        sa.Column("status", release_check_status, nullable=False),
        sa.Column("findings", postgresql.JSONB(), server_default="{}"),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("release_checks")
    op.drop_index("ix_regression_results_comparison", table_name="regression_results")
    op.drop_table("regression_results")
    op.drop_table("comparison_runs")
    op.drop_table("release_threshold_templates")
    sa.Enum(name="releasecheckstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="caseclassification").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="comparisonrunstatus").drop(op.get_bind(), checkfirst=True)
