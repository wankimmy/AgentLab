import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class RedTeamRunCreate(BaseModel):
    agent_version_id: uuid.UUID
    categories: list[str] = Field(default_factory=list)
    confirm: bool = False


class RedTeamRunEstimate(BaseModel):
    estimated_cost: float
    case_count: int


class RedTeamCaseResponse(BaseModel):
    id: uuid.UUID
    category: str
    payload: str
    response: str
    passed: bool | None
    severity: str
    promoted_case_id: uuid.UUID | None = None


class RedTeamRunDetail(BaseModel):
    id: uuid.UUID
    status: str
    agent_version_id: uuid.UUID
    categories: list[str]
    created_at: datetime
    completed_at: datetime | None
    cases: list[RedTeamCaseResponse] = Field(default_factory=list)


class PromoteResponse(BaseModel):
    evaluation_case_id: uuid.UUID
    message: str
