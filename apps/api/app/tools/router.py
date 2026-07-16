from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.models.entities import Tool
from app.schemas.tools import ToolSummary

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=list[ToolSummary])
def list_tools(user: CurrentUser, db: Session = Depends(get_db)) -> list[ToolSummary]:
    tools = db.query(Tool).order_by(Tool.name).all()
    return [
        ToolSummary(
            id=t.id,
            name=t.name,
            description=t.description,
            input_schema=t.input_schema or {},
            output_schema=t.output_schema or {},
            risk_level=t.risk_level.value,
        )
        for t in tools
    ]
