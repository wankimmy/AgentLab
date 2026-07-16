import uuid
from typing import Any

from pydantic import BaseModel, Field

from app.models.entities import DocumentStatus, JobStatus, ReadinessStatus


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str = ""
    purpose: str = ""


class CollectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    purpose: str | None = None
    planning_metadata: dict[str, Any] | None = None


class CollectionResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    purpose: str
    readiness_status: ReadinessStatus
    planning_metadata: dict[str, Any]
    document_count: int = 0
    ready_document_count: int = 0

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    id: uuid.UUID
    collection_id: uuid.UUID
    filename: str
    content_type: str
    status: DocumentStatus
    chunk_count: int
    embedding_model: str
    error_info: dict[str, Any] | None = None

    model_config = {"from_attributes": True}


class DocumentDetail(DocumentResponse):
    extracted_text: str
    chunking_settings: dict[str, Any]


class ChunkResponse(BaseModel):
    id: uuid.UUID
    content: str
    token_count: int
    page_number: int | None
    heading: str | None
    sort_order: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReadyCheckResponse(BaseModel):
    ready: bool
    readiness_status: ReadinessStatus
    checklist: dict[str, bool]
    messages: list[str]


class RetrievalDebugRequest(BaseModel):
    query: str = Field(min_length=1)
    agent_version_id: uuid.UUID | None = None
    collection_ids: list[uuid.UUID] = Field(default_factory=list)
    retrieval_config: dict[str, Any] = Field(default_factory=dict)


class RetrievalDebugChunk(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_name: str
    score: float
    heading: str | None
    page_number: int | None
    excerpt: str
    content: str


class RetrievalDebugResponse(BaseModel):
    query: str
    mode: str
    chunks: list[RetrievalDebugChunk]


class VersionCollectionsUpdate(BaseModel):
    collection_ids: list[uuid.UUID]


class VersionCollectionsResponse(BaseModel):
    agent_version_id: uuid.UUID
    collection_ids: list[uuid.UUID]


class VersionRagUpdate(BaseModel):
    rag_enabled: bool | None = None
    retrieval_config: dict[str, Any] | None = None


class ReindexResponse(BaseModel):
    job_id: uuid.UUID
    message: str
    estimated_tokens: int


class BackgroundJobResponse(BaseModel):
    id: uuid.UUID
    job_type: str
    status: JobStatus
    document_id: uuid.UUID | None
    error: str | None

    model_config = {"from_attributes": True}
