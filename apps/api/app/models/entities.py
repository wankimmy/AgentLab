import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, TimestampMixin, new_uuid


class UserRole(str, enum.Enum):
    owner = "owner"
    demo = "demo"


class RiskLevel(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class AgentStatus(str, enum.Enum):
    active = "active"
    archived = "archived"


class RuntimeType(str, enum.Enum):
    native = "native"
    langgraph = "langgraph"


class EvaluationStatus(str, enum.Enum):
    untested = "untested"
    quick_pass = "quick_pass"
    standard_pass = "standard_pass"
    release_pass = "release_pass"
    failed = "failed"


class ReleaseStatus(str, enum.Enum):
    draft = "draft"
    testing = "testing"
    needs_review = "needs_review"
    release_candidate = "release_candidate"
    release_ready = "release_ready"
    archived = "archived"


class ToolMode(str, enum.Enum):
    auto = "auto"
    approval = "approval"
    disabled = "disabled"


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.owner)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Agent(Base, TimestampMixin):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    purpose: Mapped[str | None] = mapped_column(Text)
    target_audience: Mapped[str | None] = mapped_column(Text)
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), default=RiskLevel.low)
    status: Mapped[AgentStatus] = mapped_column(Enum(AgentStatus), default=AgentStatus.active)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    active_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_versions.id", use_alter=True), nullable=True
    )
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_templates.id"), nullable=True
    )

    versions: Mapped[list["AgentVersion"]] = relationship(
        "AgentVersion",
        back_populates="agent",
        foreign_keys="AgentVersion.agent_id",
    )


class AgentVersion(Base):
    __tablename__ = "agent_versions"
    __table_args__ = (UniqueConstraint("agent_id", "version_number", name="uq_agent_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_version_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_versions.id"), nullable=True
    )
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(String(100), default="mock")
    model: Mapped[str] = mapped_column(String(100), default="mock-model")
    runtime_type: Mapped[RuntimeType] = mapped_column(Enum(RuntimeType), default=RuntimeType.native)
    model_config_json: Mapped[dict] = mapped_column("model_config", JSONB, default=dict)
    retrieval_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    tool_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    memory_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    rag_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    change_summary: Mapped[str | None] = mapped_column(Text)
    user_notes: Mapped[str | None] = mapped_column(Text)
    evaluation_status: Mapped[EvaluationStatus] = mapped_column(
        Enum(EvaluationStatus), default=EvaluationStatus.untested
    )
    release_status: Mapped[ReleaseStatus] = mapped_column(
        Enum(ReleaseStatus), default=ReleaseStatus.draft
    )
    git_commit: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    agent: Mapped["Agent"] = relationship(
        "Agent", back_populates="versions", foreign_keys=[agent_id]
    )
    version_tools: Mapped[list["AgentVersionTool"]] = relationship(back_populates="agent_version")


class Tool(Base, TimestampMixin):
    __tablename__ = "tools"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    input_schema: Mapped[dict] = mapped_column(JSONB, default=dict)
    output_schema: Mapped[dict] = mapped_column(JSONB, default=dict)
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), default=RiskLevel.low)


class AgentVersionTool(Base):
    __tablename__ = "agent_version_tools"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    agent_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_versions.id"), nullable=False
    )
    tool_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tools.id"), nullable=False)
    mode: Mapped[ToolMode] = mapped_column(Enum(ToolMode), default=ToolMode.auto)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)

    agent_version: Mapped["AgentVersion"] = relationship(back_populates="version_tools")
    tool: Mapped["Tool"] = relationship()


class AgentTemplate(Base, TimestampMixin):
    __tablename__ = "agent_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    intended_use: Mapped[str] = mapped_column(Text, default="")
    not_suitable_for: Mapped[str] = mapped_column(Text, default="")
    target_users: Mapped[str] = mapped_column(Text, default="")
    risk_level: Mapped[RiskLevel] = mapped_column(Enum(RiskLevel), default=RiskLevel.low)
    setup_effort: Mapped[str] = mapped_column(String(20), default="medium")
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent_template_versions.id", use_alter=True), nullable=True
    )

    versions: Mapped[list["AgentTemplateVersion"]] = relationship(
        "AgentTemplateVersion",
        back_populates="template",
        foreign_keys="AgentTemplateVersion.template_id",
    )


class AgentTemplateVersion(Base):
    __tablename__ = "agent_template_versions"
    __table_args__ = (
        UniqueConstraint("template_id", "version_number", name="uq_template_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    template_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_templates.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    model_config_json: Mapped[dict] = mapped_column("model_config", JSONB, default=dict)
    retrieval_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    tool_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    memory_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    recommended_collections: Mapped[list] = mapped_column(JSONB, default=list)
    example_questions: Mapped[list] = mapped_column(JSONB, default=list)
    example_answers: Mapped[list] = mapped_column(JSONB, default=list)
    eval_starter_pack: Mapped[dict] = mapped_column(JSONB, default=dict)
    judge_rubric: Mapped[dict] = mapped_column(JSONB, default=dict)
    security_test_cases: Mapped[list] = mapped_column(JSONB, default=list)
    release_thresholds: Mapped[dict] = mapped_column(JSONB, default=dict)
    data_preparation_guide: Mapped[str] = mapped_column(Text, default="")
    common_mistakes: Mapped[list] = mapped_column(JSONB, default=list)
    deployment_checklist: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    template: Mapped["AgentTemplate"] = relationship(
        "AgentTemplate", back_populates="versions", foreign_keys=[template_id]
    )
