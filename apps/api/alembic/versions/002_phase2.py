"""Phase 2: onboarding, guides, sample packs."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "002_phase2"
down_revision: str | None = "001_initial"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    guide_section_enum = postgresql.ENUM(
        "foundations", "building", "evaluating", name="guidesection", create_type=True
    )

    op.create_table(
        "onboarding_progress",
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), primary_key=True
        ),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("step_data", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "guides",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("section", guide_section_enum, nullable=False),
        sa.Column("summary", sa.Text(), server_default=""),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("screen_link", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "guide_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "guide_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("guides.id"), nullable=False
        ),
        sa.Column("heading", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), server_default=""),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
    )

    op.create_table(
        "sample_data_packs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("template_slug", sa.String(100)),
        sa.Column("manifest", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("sample_data_packs")
    op.drop_table("guide_sections")
    op.drop_table("guides")
    op.drop_table("onboarding_progress")
    op.execute("DROP TYPE IF EXISTS guidesection")
