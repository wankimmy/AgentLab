"""Initial schema: users, agents, versions, tools, templates."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    user_role = postgresql.ENUM("owner", "demo", name="userrole", create_type=True)
    risk_level = postgresql.ENUM("low", "medium", "high", name="risklevel", create_type=True)
    agent_status = postgresql.ENUM("active", "archived", name="agentstatus", create_type=True)
    runtime_type = postgresql.ENUM("native", "langgraph", name="runtimetype", create_type=True)
    eval_status = postgresql.ENUM(
        "untested",
        "quick_pass",
        "standard_pass",
        "release_pass",
        "failed",
        name="evaluationstatus",
        create_type=True,
    )
    release_status = postgresql.ENUM(
        "draft",
        "testing",
        "needs_review",
        "release_candidate",
        "release_ready",
        "archived",
        name="releasestatus",
        create_type=True,
    )
    tool_mode = postgresql.ENUM("auto", "approval", "disabled", name="toolmode", create_type=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "tools",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("input_schema", postgresql.JSONB(), server_default="{}"),
        sa.Column("output_schema", postgresql.JSONB(), server_default="{}"),
        sa.Column("risk_level", risk_level, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "agent_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("intended_use", sa.Text(), server_default=""),
        sa.Column("not_suitable_for", sa.Text(), server_default=""),
        sa.Column("target_users", sa.Text(), server_default=""),
        sa.Column("risk_level", risk_level, nullable=False),
        sa.Column("setup_effort", sa.String(20), server_default="medium"),
        sa.Column("current_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "agent_template_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "template_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_templates.id"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("system_prompt", sa.Text(), server_default=""),
        sa.Column("model_config", postgresql.JSONB(), server_default="{}"),
        sa.Column("retrieval_config", postgresql.JSONB(), server_default="{}"),
        sa.Column("tool_config", postgresql.JSONB(), server_default="{}"),
        sa.Column("memory_config", postgresql.JSONB(), server_default="{}"),
        sa.Column("recommended_collections", postgresql.JSONB(), server_default="[]"),
        sa.Column("example_questions", postgresql.JSONB(), server_default="[]"),
        sa.Column("example_answers", postgresql.JSONB(), server_default="[]"),
        sa.Column("eval_starter_pack", postgresql.JSONB(), server_default="{}"),
        sa.Column("judge_rubric", postgresql.JSONB(), server_default="{}"),
        sa.Column("security_test_cases", postgresql.JSONB(), server_default="[]"),
        sa.Column("release_thresholds", postgresql.JSONB(), server_default="{}"),
        sa.Column("data_preparation_guide", sa.Text(), server_default=""),
        sa.Column("common_mistakes", postgresql.JSONB(), server_default="[]"),
        sa.Column("deployment_checklist", postgresql.JSONB(), server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("template_id", "version_number", name="uq_template_version"),
    )

    op.create_foreign_key(
        "fk_agent_templates_current_version",
        "agent_templates",
        "agent_template_versions",
        ["current_version_id"],
        ["id"],
    )

    op.create_table(
        "agents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("purpose", sa.Text()),
        sa.Column("target_audience", sa.Text()),
        sa.Column("risk_level", risk_level, nullable=False),
        sa.Column("status", agent_status, nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String())),
        sa.Column("notes", sa.Text()),
        sa.Column("active_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_templates.id")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "agent_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column(
            "parent_version_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_versions.id")
        ),
        sa.Column("system_prompt", sa.Text(), server_default=""),
        sa.Column("provider", sa.String(100), server_default="mock"),
        sa.Column("model", sa.String(100), server_default="mock-model"),
        sa.Column("runtime_type", runtime_type, nullable=False),
        sa.Column("model_config", postgresql.JSONB(), server_default="{}"),
        sa.Column("retrieval_config", postgresql.JSONB(), server_default="{}"),
        sa.Column("tool_config", postgresql.JSONB(), server_default="{}"),
        sa.Column("memory_config", postgresql.JSONB(), server_default="{}"),
        sa.Column("rag_enabled", sa.Boolean(), server_default="false"),
        sa.Column("change_summary", sa.Text()),
        sa.Column("user_notes", sa.Text()),
        sa.Column("evaluation_status", eval_status, nullable=False),
        sa.Column("release_status", release_status, nullable=False),
        sa.Column("git_commit", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("agent_id", "version_number", name="uq_agent_version"),
    )

    op.create_foreign_key(
        "fk_agents_active_version",
        "agents",
        "agent_versions",
        ["active_version_id"],
        ["id"],
    )

    op.create_table(
        "agent_version_tools",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "agent_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "tool_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tools.id"), nullable=False
        ),
        sa.Column("mode", tool_mode, nullable=False),
        sa.Column("config", postgresql.JSONB(), server_default="{}"),
    )


def downgrade() -> None:
    op.drop_table("agent_version_tools")
    op.drop_table("agent_versions")
    op.drop_table("agents")
    op.drop_table("agent_template_versions")
    op.drop_table("agent_templates")
    op.drop_table("tools")
    op.drop_table("users")
    for name in (
        "toolmode",
        "releasestatus",
        "evaluationstatus",
        "runtimetype",
        "agentstatus",
        "risklevel",
        "userrole",
    ):
        op.execute(f"DROP TYPE IF EXISTS {name}")
