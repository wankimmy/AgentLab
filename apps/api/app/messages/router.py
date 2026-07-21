import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.judges.schemas import JudgeScoreResponse, MessageJudgeRequest
from app.judges.service import (
    _criteria_dict,
    judge_to_response,
    load_rubric_template,
    persist_judge_result,
    run_judge_sync,
)
from app.models.entities import (
    Agent,
    Conversation,
    JudgeSourceType,
    Message,
    MessageFeedback,
    MessageRole,
)
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


@router.post("/{message_id}/judge", response_model=JudgeScoreResponse)
def judge_message(
    message_id: uuid.UUID,
    body: MessageJudgeRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> JudgeScoreResponse:
    message = db.get(Message, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    if message.role != MessageRole.assistant:
        raise HTTPException(status_code=400, detail="Only assistant messages can be judged")
    conv = db.get(Conversation, message.conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    agent = db.get(Agent, conv.agent_id)
    if not agent or agent.user_id != user.id:
        raise HTTPException(status_code=404, detail="Message not found")

    prior = (
        db.query(Message)
        .filter(
            Message.conversation_id == conv.id,
            Message.created_at < message.created_at,
            Message.role == MessageRole.user,
        )
        .order_by(Message.created_at.desc())
        .first()
    )
    user_message = prior.content if prior else ""

    rubric_id = uuid.UUID(body.rubric_template_id) if body.rubric_template_id else None
    template = load_rubric_template(db, rubric_id)
    criteria = _criteria_dict(template)

    data = run_judge_sync(
        user_message=user_message,
        assistant_answer=message.content,
        criteria=criteria,
        expected_answer=body.expected_answer,
    )
    run, result = persist_judge_result(
        db,
        source_type=JudgeSourceType.message,
        source_id=message.id,
        rubric_template_id=rubric_id,
        data=data,
    )
    db.commit()
    return judge_to_response(run, result)
