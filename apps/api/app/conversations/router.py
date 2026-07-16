import json
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.models.entities import (
    Agent,
    AgentVersion,
    Conversation,
    Message,
    MessageRole,
)
from app.schemas.common import (
    ConversationCreate,
    ConversationDetail,
    ConversationSummary,
    MessageResponse,
    SendMessageRequest,
)
from app.services.chat_runtime import (
    TurnOverrides,
    get_user_conversation,
    regenerate_summary_stub,
    stream_chat_turn,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _conv_summary(c: Conversation) -> ConversationSummary:
    return ConversationSummary(
        id=c.id,
        agent_id=c.agent_id,
        agent_version_id=c.agent_version_id,
        title=c.title,
        created_at=c.created_at.isoformat(),
        updated_at=c.updated_at.isoformat(),
    )


def _message_response(msg: Message) -> MessageResponse:
    trace_id = msg.trace.id if msg.trace else None
    rating = msg.feedback.rating if msg.feedback else None
    return MessageResponse(
        id=msg.id,
        role=msg.role.value,
        content=msg.content,
        sequence=msg.sequence,
        created_at=msg.created_at.isoformat(),
        trace_id=trace_id,
        feedback_rating=rating,
    )


@router.get("", response_model=list[ConversationSummary])
def list_conversations(
    user: CurrentUser,
    db: Session = Depends(get_db),
    agent_id: uuid.UUID | None = Query(None),
) -> list[ConversationSummary]:
    query = (
        db.query(Conversation)
        .join(Agent, Agent.id == Conversation.agent_id)
        .filter(Agent.user_id == user.id)
    )
    if agent_id:
        query = query.filter(Conversation.agent_id == agent_id)
    conversations = query.order_by(Conversation.updated_at.desc()).all()
    return [_conv_summary(c) for c in conversations]


@router.post("", response_model=ConversationDetail, status_code=201)
def create_conversation(
    body: ConversationCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> ConversationDetail:
    agent = db.query(Agent).filter(Agent.id == body.agent_id, Agent.user_id == user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    version = db.get(AgentVersion, body.agent_version_id)
    if not version or version.agent_id != agent.id:
        raise HTTPException(status_code=404, detail="Agent version not found")
    conv = Conversation(
        agent_id=agent.id,
        agent_version_id=version.id,
        title=body.title,
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ConversationDetail(
        **_conv_summary(conv).model_dump(),
        messages=[],
        memory_summary=conv.memory_summary,
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation(
    conversation_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> ConversationDetail:
    conv = (
        db.query(Conversation)
        .options(
            joinedload(Conversation.messages).joinedload(Message.trace),
            joinedload(Conversation.messages).joinedload(Message.feedback),
        )
        .join(Agent, Agent.id == Conversation.agent_id)
        .filter(Conversation.id == conversation_id, Agent.user_id == user.id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetail(
        **_conv_summary(conv).model_dump(),
        messages=[_message_response(m) for m in conv.messages],
        memory_summary=conv.memory_summary,
    )


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> None:
    conv = get_user_conversation(db, conversation_id, user.id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()


@router.post("/{conversation_id}/clear", response_model=ConversationDetail)
def clear_conversation(
    conversation_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> ConversationDetail:
    conv = (
        db.query(Conversation)
        .options(joinedload(Conversation.messages))
        .join(Agent, Agent.id == Conversation.agent_id)
        .filter(Conversation.id == conversation_id, Agent.user_id == user.id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    from app.models.entities import ChatTrace, TraceEvent

    for msg in list(conv.messages):
        trace = db.query(ChatTrace).filter(ChatTrace.message_id == msg.id).first()
        if trace:
            db.query(TraceEvent).filter(TraceEvent.trace_id == trace.id).delete()
            db.delete(trace)
        db.delete(msg)
    conv.memory_summary = None
    conv.memory_summary_at = None
    db.commit()
    db.refresh(conv)
    return ConversationDetail(
        **_conv_summary(conv).model_dump(),
        messages=[],
        memory_summary=None,
    )


@router.post("/{conversation_id}/summary/regenerate", response_model=ConversationDetail)
def regenerate_summary(
    conversation_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> ConversationDetail:
    conv = (
        db.query(Conversation)
        .options(
            joinedload(Conversation.messages).joinedload(Message.trace),
            joinedload(Conversation.messages).joinedload(Message.feedback),
        )
        .join(Agent, Agent.id == Conversation.agent_id)
        .filter(Conversation.id == conversation_id, Agent.user_id == user.id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.memory_summary = regenerate_summary_stub(conv)
    conv.memory_summary_at = datetime.now(conv.updated_at.tzinfo)
    db.commit()
    db.refresh(conv)
    return ConversationDetail(
        **_conv_summary(conv).model_dump(),
        messages=[_message_response(m) for m in conv.messages],
        memory_summary=conv.memory_summary,
    )


@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: uuid.UUID,
    body: SendMessageRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    conv = (
        db.query(Conversation)
        .options(joinedload(Conversation.messages))
        .join(Agent, Agent.id == Conversation.agent_id)
        .filter(Conversation.id == conversation_id, Agent.user_id == user.id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    version = db.get(AgentVersion, conv.agent_version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Agent version not found")

    overrides_raw = body.overrides or {}
    overrides = TurnOverrides(
        system_prompt=overrides_raw.get("system_prompt"),
        model=overrides_raw.get("model"),
        temperature=overrides_raw.get("temperature"),
        memory_mode=overrides_raw.get("memory_mode"),
    )

    async def event_generator():
        async for result in stream_chat_turn(db, conv, version, body.content, overrides):
            yield f"event: {result.event_type}\ndata: {json.dumps(result.data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/{conversation_id}/messages/{message_id}/regenerate")
async def regenerate_message(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> StreamingResponse:
    conv = (
        db.query(Conversation)
        .options(joinedload(Conversation.messages))
        .join(Agent, Agent.id == Conversation.agent_id)
        .filter(Conversation.id == conversation_id, Agent.user_id == user.id)
        .first()
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    target = next((m for m in conv.messages if m.id == message_id), None)
    if not target or target.role != MessageRole.assistant:
        raise HTTPException(status_code=404, detail="Assistant message not found")
    prior_user = next(
        (
            m
            for m in reversed(conv.messages)
            if m.sequence < target.sequence and m.role == MessageRole.user
        ),
        None,
    )
    if not prior_user:
        raise HTTPException(status_code=400, detail="No user message to regenerate from")
    from app.models.entities import ChatTrace, TraceEvent

    to_delete = [m for m in conv.messages if m.sequence >= target.sequence]
    for msg in to_delete:
        trace = db.query(ChatTrace).filter(ChatTrace.message_id == msg.id).first()
        if trace:
            db.query(TraceEvent).filter(TraceEvent.trace_id == trace.id).delete()
            db.delete(trace)
        db.delete(msg)
    db.commit()
    db.refresh(conv)

    version = db.get(AgentVersion, conv.agent_version_id)
    if not version:
        raise HTTPException(status_code=404, detail="Agent version not found")

    async def event_generator():
        async for result in stream_chat_turn(db, conv, version, prior_user.content, None):
            yield f"event: {result.event_type}\ndata: {json.dumps(result.data)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")
