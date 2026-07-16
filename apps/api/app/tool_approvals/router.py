import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.models.entities import Agent, Conversation, ToolApproval, ToolApprovalStatus
from app.schemas.tools import ToolApprovalResponse

router = APIRouter(prefix="/tool-approvals", tags=["tool-approvals"])


def _get_user_approval(approval_id: uuid.UUID, user: CurrentUser, db: Session) -> ToolApproval:
    approval = (
        db.query(ToolApproval)
        .join(Conversation, Conversation.id == ToolApproval.conversation_id)
        .join(Agent, Agent.id == Conversation.agent_id)
        .filter(ToolApproval.id == approval_id, Agent.user_id == user.id)
        .first()
    )
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    return approval


@router.post("/{approval_id}/approve", response_model=ToolApprovalResponse)
def approve_tool(
    approval_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> ToolApprovalResponse:
    approval = _get_user_approval(approval_id, user, db)
    if approval.status != ToolApprovalStatus.pending:
        raise HTTPException(status_code=400, detail="Approval is not pending")
    approval.status = ToolApprovalStatus.approved
    approval.decided_by = user.id
    approval.decided_at = datetime.now(approval.created_at.tzinfo)
    db.commit()
    db.refresh(approval)
    return ToolApprovalResponse.model_validate(approval)


@router.post("/{approval_id}/reject", response_model=ToolApprovalResponse)
def reject_tool(
    approval_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> ToolApprovalResponse:
    approval = _get_user_approval(approval_id, user, db)
    if approval.status != ToolApprovalStatus.pending:
        raise HTTPException(status_code=400, detail="Approval is not pending")
    approval.status = ToolApprovalStatus.rejected
    approval.decided_by = user.id
    approval.decided_at = datetime.now(approval.created_at.tzinfo)
    db.commit()
    db.refresh(approval)
    return ToolApprovalResponse.model_validate(approval)
