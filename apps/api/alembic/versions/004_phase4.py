"""Phase 4: knowledge collections, documents, chunks, jobs."""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "004_phase4"
down_revision: str | None = "003_phase3"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    readiness = postgresql.ENUM(
        "not_started",
        "needs_preparation",
        "ready_for_testing",
        "ready",
        name="readinessstatus",
        create_type=True,
    )
    doc_status = postgresql.ENUM(
        "uploaded",
        "processing",
        "ready",
        "failed",
        "archived",
        name="documentstatus",
        create_type=True,
    )
    job_status = postgresql.ENUM(
        "pending",
        "running",
        "completed",
        "failed",
        name="jobstatus",
        create_type=True,
    )

    op.create_table(
        "knowledge_collections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("purpose", sa.Text(), server_default=""),
        sa.Column("readiness_status", readiness, server_default="not_started"),
        sa.Column("planning_metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "collection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_collections.id"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), server_default=""),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("status", doc_status, server_default="uploaded"),
        sa.Column("chunk_count", sa.Integer(), server_default="0"),
        sa.Column("embedding_model", sa.String(100), server_default="mock-embed"),
        sa.Column("chunking_settings", postgresql.JSONB(), server_default="{}"),
        sa.Column("extracted_text", sa.Text(), server_default=""),
        sa.Column("error_info", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "document_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("documents.id"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), server_default="0"),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("heading", sa.String(255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}"),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute("ALTER TABLE document_chunks ADD COLUMN embedding vector(1536)")
    op.execute(
        "ALTER TABLE document_chunks ADD COLUMN content_tsv tsvector "
        "GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED"
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding ON document_chunks "
        "USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_content_tsv ON document_chunks USING gin (content_tsv)"
    )

    op.create_table(
        "agent_version_collections",
        sa.Column(
            "agent_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_versions.id"),
            primary_key=True,
        ),
        sa.Column(
            "collection_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("knowledge_collections.id"),
            primary_key=True,
        ),
    )

    op.create_table(
        "background_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_type", sa.String(50), nullable=False),
        sa.Column("status", job_status, server_default="pending"),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("documents.id")),
        sa.Column("payload", postgresql.JSONB(), server_default="{}"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("background_jobs")
    op.drop_table("agent_version_collections")
    op.drop_table("document_chunks")
    op.drop_table("documents")
    op.drop_table("knowledge_collections")
    op.execute("DROP TYPE IF EXISTS jobstatus")
    op.execute("DROP TYPE IF EXISTS documentstatus")
    op.execute("DROP TYPE IF EXISTS readinessstatus")
