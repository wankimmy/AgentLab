import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.models.entities import Agent, Conversation, Message, MessageFeedback
from app.schemas.common import MessageFeedbackCreate, MessageFeedbackResponse

router = APIRouter(prefix="/messages", tags=["messages"])


@router.post("/{message_id}/feedback", response_model=MessageFeedbackResponse)
def submit_feedback(
    message_id: uuid.UUID,
    body: MessageFeedbackCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> MessageFeedbackResponse:
    message = db.get(Message, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    conv = db.get(Conversation, message.conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    agent = db.get(Agent, conv.agent_id)
    if not agent or agent.user_id != user.id:
        raise HTTPException(status_code=404, detail="Message not found")

    existing = db.query(MessageFeedback).filter(MessageFeedback.message_id == message_id).first()
    if existing:
        existing.rating = body.rating
        existing.notes = body.notes
        feedback = existing
    else:
        feedback = MessageFeedback(
            message_id=message_id,
            user_id=user.id,
            rating=body.rating,
            notes=body.notes,
        )
        db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return MessageFeedbackResponse(
        message_id=feedback.message_id,
        rating=feedback.rating,
        notes=feedback.notes,
    )
