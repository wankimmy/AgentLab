import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.models.entities import Agent, ChatTrace, Conversation, Message
from app.schemas.common import TraceDetail, TraceEventResponse, TraceSummary

router = APIRouter(prefix="/traces", tags=["traces"])


@router.get("", response_model=list[TraceSummary])
def list_traces(
    user: CurrentUser,
    db: Session = Depends(get_db),
    agent_id: uuid.UUID | None = Query(None),
) -> list[TraceSummary]:
    query = (
        db.query(ChatTrace)
        .join(Message, Message.id == ChatTrace.message_id)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .join(Agent, Agent.id == Conversation.agent_id)
        .filter(Agent.user_id == user.id)
    )
    if agent_id:
        query = query.filter(Conversation.agent_id == agent_id)
    traces = query.order_by(ChatTrace.created_at.desc()).limit(50).all()
    return [
        TraceSummary(
            id=t.id,
            message_id=t.message_id,
            provider=t.provider,
            model=t.model,
            duration_ms=t.duration_ms,
            input_tokens=t.input_tokens,
            output_tokens=t.output_tokens,
            estimated_cost=float(t.estimated_cost),
            created_at=t.created_at.isoformat(),
        )
        for t in traces
    ]


@router.get("/{trace_id}", response_model=TraceDetail)
def get_trace(
    trace_id: uuid.UUID,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> TraceDetail:
    trace = (
        db.query(ChatTrace)
        .options(joinedload(ChatTrace.events))
        .join(Message, Message.id == ChatTrace.message_id)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .join(Agent, Agent.id == Conversation.agent_id)
        .filter(ChatTrace.id == trace_id, Agent.user_id == user.id)
        .first()
    )
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return TraceDetail(
        id=trace.id,
        message_id=trace.message_id,
        agent_version_id=trace.agent_version_id,
        provider=trace.provider,
        model=trace.model,
        runtime=trace.runtime,
        duration_ms=trace.duration_ms,
        ttft_ms=trace.ttft_ms,
        input_tokens=trace.input_tokens,
        output_tokens=trace.output_tokens,
        estimated_cost=float(trace.estimated_cost),
        retrieved_chunks=trace.retrieved_chunks or [],
        tool_requests=trace.tool_requests or [],
        tool_results=trace.tool_results or [],
        overrides=trace.overrides or {},
        errors=trace.errors,
        events=[
            TraceEventResponse(
                event_type=e.event_type,
                payload=e.payload,
                timestamp=e.timestamp.isoformat(),
            )
            for e in trace.events
        ],
    )
