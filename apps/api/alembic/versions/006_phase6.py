"""Phase 6: evaluation datasets, cases, runs, results."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "006_phase6"
down_revision: str | None = "005_phase5"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    case_severity = postgresql.ENUM(
        "critical", "high", "medium", "low", name="caseseverity", create_type=True
    )
    case_status = postgresql.ENUM("draft", "approved", name="casestatus", create_type=True)
    eval_mode = postgresql.ENUM("quick", "standard", "release", name="evalmode", create_type=True)
    run_status = postgresql.ENUM(
        "pending", "running", "completed", "failed", "cancelled", name="runstatus", create_type=True
    )
    result_status = postgresql.ENUM(
        "passed", "failed", "error", "needs_review", name="resultstatus", create_type=True
    )
    metric_type = postgresql.ENUM(
        "deterministic", "semantic", "rag", "tool", "judge", name="metrictype", create_type=True
    )

    op.create_table(
        "evaluation_datasets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id")),
        sa.Column(
            "template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_templates.id")
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "evaluation_dataset_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_datasets.id"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("dataset_id", "version_number", name="uq_dataset_version"),
    )

    op.create_table(
        "evaluation_cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "dataset_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_dataset_versions.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("category", sa.String(100), server_default=""),
        sa.Column("user_message", sa.Text(), nullable=False),
        sa.Column("conversation_history", postgresql.JSONB()),
        sa.Column("expected_answer", sa.Text()),
        sa.Column("expected_behaviour", sa.Text()),
        sa.Column("required_keywords", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("forbidden_keywords", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("forbidden_claims", postgresql.ARRAY(sa.Text()), server_default="{}"),
        sa.Column("expected_source", sa.String(255)),
        sa.Column("expected_citation", sa.String(255)),
        sa.Column("expected_tool", sa.String(100)),
        sa.Column("expected_tool_args", postgresql.JSONB()),
        sa.Column("max_latency_ms", sa.Integer()),
        sa.Column("max_tokens", sa.Integer()),
        sa.Column("max_cost", sa.Numeric(12, 6)),
        sa.Column("min_judge_score", sa.Numeric(5, 2)),
        sa.Column("severity", case_severity, server_default="medium"),
        sa.Column("importance_weight", sa.Numeric(5, 2), server_default="1"),
        sa.Column("tags", postgresql.ARRAY(sa.String()), server_default="{}"),
        sa.Column("notes", sa.Text()),
        sa.Column("requires_human_review", sa.Boolean(), server_default="false"),
        sa.Column("status", case_status, server_default="approved"),
    )

    op.create_table(
        "evaluation_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "dataset_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_dataset_versions.id"),
            nullable=False,
        ),
        sa.Column("mode", eval_mode, server_default="quick"),
        sa.Column("status", run_status, server_default="pending"),
        sa.Column("judge_enabled", sa.Boolean(), server_default="false"),
        sa.Column("judge_model", sa.String(100)),
        sa.Column("pass_rate", sa.Numeric(5, 4)),
        sa.Column("total_cost", sa.Numeric(12, 6)),
        sa.Column("mlflow_run_id", sa.String(100)),
        sa.Column("config_snapshot", postgresql.JSONB(), server_default="{}"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_evaluation_runs_status", "evaluation_runs", ["status"])

    op.create_table(
        "evaluation_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_cases.id"),
            nullable=False,
        ),
        sa.Column("status", result_status, nullable=False),
        sa.Column("actual_answer", sa.Text(), server_default=""),
        sa.Column("overall_pass", sa.Boolean(), server_default="false"),
        sa.Column("failure_explanation", sa.Text()),
        sa.Column("trace_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_traces.id")),
        sa.Column("latency_ms", sa.Integer(), server_default="0"),
        sa.Column("tokens", sa.Integer(), server_default="0"),
        sa.Column("cost", sa.Numeric(12, 6), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_evaluation_results_run_id", "evaluation_results", ["run_id"])

    op.create_table(
        "metric_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("evaluation_results.id"),
            nullable=False,
        ),
        sa.Column("metric_name", sa.String(100), nullable=False),
        sa.Column("metric_type", metric_type, nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Numeric(8, 4)),
        sa.Column("threshold", sa.Numeric(8, 4)),
        sa.Column("details", postgresql.JSONB(), server_default="{}"),
    )
    op.create_index("ix_metric_results_result_id", "metric_results", ["result_id"])


def downgrade() -> None:
    op.drop_table("metric_results")
    op.drop_table("evaluation_results")
    op.drop_table("evaluation_runs")
    op.drop_table("evaluation_cases")
    op.drop_table("evaluation_dataset_versions")
    op.drop_table("evaluation_datasets")
    op.execute("DROP TYPE IF EXISTS metrictype")
    op.execute("DROP TYPE IF EXISTS resultstatus")
    op.execute("DROP TYPE IF EXISTS runstatus")
    op.execute("DROP TYPE IF EXISTS evalmode")
    op.execute("DROP TYPE IF EXISTS casestatus")
    op.execute("DROP TYPE IF EXISTS caseseverity")
