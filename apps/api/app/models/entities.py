import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
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


class GuideSection(str, enum.Enum):
    foundations = "foundations"
    building = "building"
    evaluating = "evaluating"


class OnboardingProgress(Base, TimestampMixin):
    __tablename__ = "onboarding_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    current_step: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    step_data: Mapped[dict] = mapped_column(JSONB, default=dict)


class Guide(Base, TimestampMixin):
    __tablename__ = "guides"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    section: Mapped[GuideSection] = mapped_column(Enum(GuideSection), nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    screen_link: Mapped[str | None] = mapped_column(String(255))

    sections: Mapped[list["GuideSectionContent"]] = relationship(
        back_populates="guide", order_by="GuideSectionContent.sort_order"
    )


class GuideSectionContent(Base):
    __tablename__ = "guide_sections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    guide_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("guides.id"), nullable=False)
    heading: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    guide: Mapped["Guide"] = relationship(back_populates="sections")


class SampleDataPack(Base, TimestampMixin):
    __tablename__ = "sample_data_packs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    template_slug: Mapped[str | None] = mapped_column(String(100))
    manifest: Mapped[dict] = mapped_column(JSONB, default=dict)


class MessageRole(str, enum.Enum):
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"


class ModelRegistry(Base, TimestampMixin):
    __tablename__ = "model_registry"
    __table_args__ = (UniqueConstraint("provider", "model", name="uq_model_registry"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    context_limit: Mapped[int] = mapped_column(Integer, default=8192)
    streaming: Mapped[bool] = mapped_column(Boolean, default=True)
    tool_calling: Mapped[bool] = mapped_column(Boolean, default=False)
    structured_output: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class ModelPricing(Base):
    __tablename__ = "model_pricing"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    input_token_cost: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=Decimal("0"))
    output_token_cost: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=Decimal("0"))
    effective_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"), nullable=False)
    agent_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_versions.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), default="New conversation")
    memory_summary: Mapped[str | None] = mapped_column(Text)
    memory_summary_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", order_by="Message.sequence"
    )


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("conversation_id", "sequence", name="uq_message_sequence"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"), nullable=False
    )
    role: Mapped[MessageRole] = mapped_column(Enum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, default="")
    tool_calls: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(100))
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    trace: Mapped["ChatTrace | None"] = relationship(back_populates="message", uselist=False)
    feedback: Mapped["MessageFeedback | None"] = relationship(
        back_populates="message", uselist=False
    )


class ChatTrace(Base):
    __tablename__ = "chat_traces"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id"), nullable=False, unique=True
    )
    agent_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_versions.id"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    runtime: Mapped[str] = mapped_column(String(50), default="native")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    ttft_ms: Mapped[int | None] = mapped_column(Integer)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(12, 8), default=Decimal("0"))
    retrieved_chunks: Mapped[list] = mapped_column(JSONB, default=list)
    tool_requests: Mapped[list] = mapped_column(JSONB, default=list)
    tool_results: Mapped[list] = mapped_column(JSONB, default=list)
    guardrail_results: Mapped[list] = mapped_column(JSONB, default=list)
    overrides: Mapped[dict] = mapped_column(JSONB, default=dict)
    errors: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    message: Mapped["Message"] = relationship(back_populates="trace")
    events: Mapped[list["TraceEvent"]] = relationship(
        back_populates="trace", order_by="TraceEvent.timestamp"
    )


class TraceEvent(Base):
    __tablename__ = "trace_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    trace_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("chat_traces.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    trace: Mapped["ChatTrace"] = relationship(back_populates="events")


class MessageFeedback(Base, TimestampMixin):
    __tablename__ = "message_feedback"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    message_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("messages.id"), nullable=False, unique=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)

    message: Mapped["Message"] = relationship(back_populates="feedback")
