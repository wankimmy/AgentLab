import uuid

from pydantic import BaseModel, Field

from app.models.entities import ToolApprovalStatus


class ToolSummary(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    risk_level: str

    model_config = {"from_attributes": True}


class ToolApprovalResponse(BaseModel):
    id: uuid.UUID
    status: ToolApprovalStatus
    tool_name: str
    arguments: dict

    model_config = {"from_attributes": True}


class VersionToolsUpdate(BaseModel):
    tool_config: dict = Field(default_factory=dict)
