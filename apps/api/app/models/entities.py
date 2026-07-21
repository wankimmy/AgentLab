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


class ReadinessStatus(str, enum.Enum):
    not_started = "not_started"
    needs_preparation = "needs_preparation"
    ready_for_testing = "ready_for_testing"
    ready = "ready"


class DocumentStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    ready = "ready"
    failed = "failed"
    archived = "archived"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class KnowledgeCollection(Base, TimestampMixin):
    __tablename__ = "knowledge_collections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    purpose: Mapped[str] = mapped_column(Text, default="")
    readiness_status: Mapped[ReadinessStatus] = mapped_column(
        Enum(ReadinessStatus), default=ReadinessStatus.not_started
    )
    planning_metadata: Mapped[dict] = mapped_column(JSONB, default=dict)

    documents: Mapped[list["Document"]] = relationship(back_populates="collection")


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_collections.id"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(100), default="")
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.uploaded
    )
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding_model: Mapped[str] = mapped_column(String(100), default="mock-embed")
    chunking_settings: Mapped[dict] = mapped_column(JSONB, default=dict)
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    error_info: Mapped[dict | None] = mapped_column(JSONB)

    collection: Mapped["KnowledgeCollection"] = relationship(back_populates="documents")
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        back_populates="document", order_by="DocumentChunk.sort_order"
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    page_number: Mapped[int | None] = mapped_column(Integer)
    heading: Mapped[str | None] = mapped_column(String(255))
    chunk_metadata: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    document: Mapped["Document"] = relationship(back_populates="chunks")


class AgentVersionCollection(Base):
    __tablename__ = "agent_version_collections"

    agent_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_versions.id"), primary_key=True
    )
    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("knowledge_collections.id"), primary_key=True
    )


class BackgroundJob(Base, TimestampMixin):
    __tablename__ = "background_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.pending)
    document_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("documents.id"))
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text)


class ToolApprovalStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    expired = "expired"


class ToolApproval(Base):
    __tablename__ = "tool_approvals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id"), nullable=False
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("messages.id"))
    trace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chat_traces.id"))
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    tool_call_id: Mapped[str] = mapped_column(String(100), nullable=False)
    arguments: Mapped[dict] = mapped_column(JSONB, default=dict)
    status: Mapped[ToolApprovalStatus] = mapped_column(
        Enum(ToolApprovalStatus), default=ToolApprovalStatus.pending
    )
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    trace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chat_traces.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CaseSeverity(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class CaseStatus(str, enum.Enum):
    draft = "draft"
    approved = "approved"


class EvalMode(str, enum.Enum):
    quick = "quick"
    standard = "standard"
    release = "release"


class RunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class ResultStatus(str, enum.Enum):
    passed = "passed"
    failed = "failed"
    error = "error"
    needs_review = "needs_review"


class MetricType(str, enum.Enum):
    deterministic = "deterministic"
    semantic = "semantic"
    rag = "rag"
    tool = "tool"
    judge = "judge"


class EvaluationDataset(Base, TimestampMixin):
    __tablename__ = "evaluation_datasets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agents.id"))
    template_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("agent_templates.id"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")

    versions: Mapped[list["EvaluationDatasetVersion"]] = relationship(
        back_populates="dataset", order_by="EvaluationDatasetVersion.version_number"
    )


class EvaluationDatasetVersion(Base):
    __tablename__ = "evaluation_dataset_versions"
    __table_args__ = (UniqueConstraint("dataset_id", "version_number", name="uq_dataset_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    dataset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluation_datasets.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    dataset: Mapped["EvaluationDataset"] = relationship(back_populates="versions")
    cases: Mapped[list["EvaluationCase"]] = relationship(back_populates="dataset_version")


class EvaluationCase(Base):
    __tablename__ = "evaluation_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluation_dataset_versions.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="")
    user_message: Mapped[str] = mapped_column(Text, nullable=False)
    conversation_history: Mapped[dict | None] = mapped_column(JSONB)
    expected_answer: Mapped[str | None] = mapped_column(Text)
    expected_behaviour: Mapped[str | None] = mapped_column(Text)
    required_keywords: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    forbidden_keywords: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    forbidden_claims: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    expected_source: Mapped[str | None] = mapped_column(String(255))
    expected_citation: Mapped[str | None] = mapped_column(String(255))
    expected_tool: Mapped[str | None] = mapped_column(String(100))
    expected_tool_args: Mapped[dict | None] = mapped_column(JSONB)
    max_latency_ms: Mapped[int | None] = mapped_column(Integer)
    max_tokens: Mapped[int | None] = mapped_column(Integer)
    max_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    min_judge_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    severity: Mapped[CaseSeverity] = mapped_column(Enum(CaseSeverity), default=CaseSeverity.medium)
    importance_weight: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("1"))
    tags: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    requires_human_review: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[CaseStatus] = mapped_column(Enum(CaseStatus), default=CaseStatus.approved)

    dataset_version: Mapped["EvaluationDatasetVersion"] = relationship(back_populates="cases")


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    agent_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_versions.id"), nullable=False
    )
    dataset_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluation_dataset_versions.id"), nullable=False
    )
    mode: Mapped[EvalMode] = mapped_column(Enum(EvalMode), default=EvalMode.quick)
    status: Mapped[RunStatus] = mapped_column(Enum(RunStatus), default=RunStatus.pending)
    judge_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    judge_model: Mapped[str | None] = mapped_column(String(100))
    pass_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    total_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    mlflow_run_id: Mapped[str | None] = mapped_column(String(100))
    config_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    results: Mapped[list["EvaluationResult"]] = relationship(back_populates="run")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_runs.id"), nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("evaluation_cases.id"), nullable=False)
    status: Mapped[ResultStatus] = mapped_column(Enum(ResultStatus), nullable=False)
    actual_answer: Mapped[str] = mapped_column(Text, default="")
    overall_pass: Mapped[bool] = mapped_column(Boolean, default=False)
    failure_explanation: Mapped[str | None] = mapped_column(Text)
    trace_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("chat_traces.id"))
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run: Mapped["EvaluationRun"] = relationship(back_populates="results")
    metrics: Mapped[list["MetricResult"]] = relationship(back_populates="result")


class MetricResult(Base):
    __tablename__ = "metric_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    result_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluation_results.id"), nullable=False
    )
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False)
    metric_type: Mapped[MetricType] = mapped_column(Enum(MetricType), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    threshold: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    details: Mapped[dict] = mapped_column(JSONB, default=dict)

    result: Mapped["EvaluationResult"] = relationship(back_populates="metrics")


class JudgeSourceType(str, enum.Enum):
    message = "message"
    evaluation_result = "evaluation_result"
    multi = "multi"


class JudgeRunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class HumanReviewVerdict(str, enum.Enum):
    pass_ = "pass"
    fail = "fail"
    needs_review = "needs_review"


class JudgeRubricTemplate(Base, TimestampMixin):
    __tablename__ = "judge_rubric_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    criteria: Mapped[dict] = mapped_column(JSONB, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)


class JudgeRun(Base):
    __tablename__ = "judge_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    rubric_template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("judge_rubric_templates.id")
    )
    source_type: Mapped[JudgeSourceType] = mapped_column(Enum(JudgeSourceType), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), default="mock")
    model: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[JudgeRunStatus] = mapped_column(
        Enum(JudgeRunStatus), default=JudgeRunStatus.pending
    )
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=Decimal("0"))
    config_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    results: Mapped[list["JudgeResult"]] = relationship(back_populates="judge_run")


class JudgeResult(Base):
    __tablename__ = "judge_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    judge_run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("judge_runs.id"), nullable=False)
    evaluation_result_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evaluation_results.id")
    )
    criteria_scores: Mapped[dict] = mapped_column(JSONB, default=dict)
    overall_score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    explanation: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    structured_raw: Mapped[dict] = mapped_column(JSONB, default=dict)
    judge_index: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    judge_run: Mapped["JudgeRun"] = relationship(back_populates="results")


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    evaluation_result_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("evaluation_results.id"), unique=True, nullable=False
    )
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    verdict: Mapped[HumanReviewVerdict] = mapped_column(Enum(HumanReviewVerdict), nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    issue_category: Mapped[str | None] = mapped_column(String(100))
    suggested_improvement: Mapped[str | None] = mapped_column(Text)
    preferred_answer: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class BlindAbReview(Base):
    __tablename__ = "blind_ab_reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    left_message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id"), nullable=False)
    right_message_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("messages.id"), nullable=False)
    left_label: Mapped[str] = mapped_column(String(255), nullable=False)
    right_label: Mapped[str] = mapped_column(String(255), nullable=False)
    preference: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class ComparisonRunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class CaseClassification(str, enum.Enum):
    improved = "improved"
    regressed = "regressed"
    unchanged = "unchanged"


class ReleaseCheckStatus(str, enum.Enum):
    passed = "passed"
    failed = "failed"
    blocked = "blocked"


class ReleaseThresholdTemplate(Base, TimestampMixin):
    __tablename__ = "release_threshold_templates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    rules: Mapped[dict] = mapped_column(JSONB, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)


class ComparisonRun(Base):
    __tablename__ = "comparison_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    baseline_agent_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_versions.id"), nullable=False
    )
    candidate_agent_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_versions.id"), nullable=False
    )
    baseline_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("evaluation_runs.id"))
    candidate_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("evaluation_runs.id"))
    status: Mapped[ComparisonRunStatus] = mapped_column(
        Enum(ComparisonRunStatus), default=ComparisonRunStatus.pending
    )
    baseline_pass_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    candidate_pass_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 4))
    pass_rate_delta: Mapped[Decimal | None] = mapped_column(Numeric(6, 4))
    config_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    ai_summary: Mapped[str | None] = mapped_column(Text)
    ai_summary_status: Mapped[str] = mapped_column(String(30), default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    regressions: Mapped[list["RegressionResult"]] = relationship(back_populates="comparison_run")


class PromptRecommendationSource(str, enum.Enum):
    analyse = "analyse"
    failed_cases = "failed_cases"


class PromptRecommendationStatus(str, enum.Enum):
    draft = "draft"
    accepted = "accepted"
    dismissed = "dismissed"


class PromptRecommendation(Base):
    __tablename__ = "prompt_recommendations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    agent_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_versions.id"), nullable=False
    )
    source: Mapped[PromptRecommendationSource] = mapped_column(
        Enum(PromptRecommendationSource), nullable=False
    )
    suggestions: Mapped[list] = mapped_column(JSONB, default=list)
    status: Mapped[PromptRecommendationStatus] = mapped_column(
        Enum(PromptRecommendationStatus), default=PromptRecommendationStatus.draft
    )
    estimated_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class RedTeamRunStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class RedTeamRun(Base):
    __tablename__ = "red_team_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    agent_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_versions.id"), nullable=False
    )
    status: Mapped[RedTeamRunStatus] = mapped_column(
        Enum(RedTeamRunStatus), default=RedTeamRunStatus.pending
    )
    categories: Mapped[list] = mapped_column(JSONB, default=list)
    config_snapshot: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    cases: Mapped[list["RedTeamCase"]] = relationship(back_populates="run")


class RedTeamCase(Base):
    __tablename__ = "red_team_cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    red_team_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("red_team_runs.id"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, default="")
    passed: Mapped[bool | None] = mapped_column(Boolean)
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    promoted_case_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("evaluation_cases.id")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    run: Mapped["RedTeamRun"] = relationship(back_populates="cases")


class RegressionResult(Base):
    __tablename__ = "regression_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    comparison_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comparison_runs.id"), nullable=False
    )
    case_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("evaluation_cases.id"))
    case_name: Mapped[str] = mapped_column(String(255), default="")
    classification: Mapped[CaseClassification] = mapped_column(Enum(CaseClassification), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    details: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    comparison_run: Mapped["ComparisonRun"] = relationship(back_populates="regressions")


class ReleaseCheck(Base):
    __tablename__ = "release_checks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    agent_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_versions.id"), nullable=False
    )
    eval_run_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("evaluation_runs.id"))
    threshold_template_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("release_threshold_templates.id")
    )
    status: Mapped[ReleaseCheckStatus] = mapped_column(Enum(ReleaseCheckStatus), nullable=False)
    findings: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
