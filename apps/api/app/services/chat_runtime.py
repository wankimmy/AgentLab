import hashlib
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.entities import (
    Agent,
    AgentVersion,
    ChatTrace,
    Conversation,
    Message,
    MessageRole,
    TraceEvent,
)
from app.providers.base import ChatRequest
from app.providers.registry import get_provider
from app.services.cost_service import estimate_cost

SUMMARY_RECENT_MESSAGES = 20


@dataclass
class TurnOverrides:
    system_prompt: str | None = None
    model: str | None = None
    temperature: float | None = None
    memory_mode: str | None = None


@dataclass
class StreamResult:
    event_type: str
    data: dict


def _memory_mode(version: AgentVersion, overrides: TurnOverrides | None) -> str:
    if overrides and overrides.memory_mode:
        return overrides.memory_mode
    return version.memory_config.get("mode", "conversation")


def assemble_messages(
    version: AgentVersion,
    conversation: Conversation,
    user_content: str,
    overrides: TurnOverrides | None,
) -> list[dict]:
    system_prompt = (
        overrides.system_prompt if overrides and overrides.system_prompt else version.system_prompt
    )
    mode = _memory_mode(version, overrides)
    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    prior = sorted(
        [m for m in conversation.messages if m.role != MessageRole.system],
        key=lambda m: m.sequence,
    )
    if mode == "none":
        messages.append({"role": "user", "content": user_content})
        return messages

    if mode == "summarised" and conversation.memory_summary:
        messages.append(
            {
                "role": "system",
                "content": f"Conversation summary:\n{conversation.memory_summary}",
            }
        )
        recent = prior[-SUMMARY_RECENT_MESSAGES:]
    else:
        recent = prior

    for msg in recent:
        messages.append({"role": msg.role.value, "content": msg.content})
    messages.append({"role": "user", "content": user_content})
    return messages


def regenerate_summary_stub(conversation: Conversation) -> str:
    texts = [
        m.content
        for m in conversation.messages
        if m.role in (MessageRole.user, MessageRole.assistant)
    ]
    combined = "\n".join(texts[-10:])
    digest = hashlib.sha256(combined.encode()).hexdigest()[:8]
    preview = combined[:400] + ("..." if len(combined) > 400 else "")
    return f"[summary:{digest}] {preview}"


async def stream_chat_turn(
    db: Session,
    conversation: Conversation,
    version: AgentVersion,
    user_content: str,
    overrides: TurnOverrides | None = None,
) -> AsyncIterator[StreamResult]:
    next_seq = len(conversation.messages)
    user_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.user,
        content=user_content,
        sequence=next_seq,
    )
    db.add(user_msg)
    db.flush()

    provider_name = version.provider
    model = overrides.model if overrides and overrides.model else version.model
    temperature = (
        overrides.temperature
        if overrides and overrides.temperature is not None
        else version.model_config_json.get("temperature", 0.3)
    )
    max_tokens = version.model_config_json.get("max_tokens", 1024)

    messages = assemble_messages(version, conversation, user_content, overrides)
    request = ChatRequest(
        model=model,
        messages=messages,
        temperature=float(temperature),
        max_tokens=int(max_tokens),
    )

    provider = get_provider(provider_name)
    assistant_msg = Message(
        conversation_id=conversation.id,
        role=MessageRole.assistant,
        content="",
        sequence=next_seq + 1,
    )
    db.add(assistant_msg)
    db.flush()

    trace = ChatTrace(
        message_id=assistant_msg.id,
        agent_version_id=version.id,
        provider=provider_name,
        model=model,
        runtime=version.runtime_type.value,
        overrides={
            k: v
            for k, v in {
                "system_prompt": overrides.system_prompt if overrides else None,
                "model": overrides.model if overrides else None,
                "temperature": overrides.temperature if overrides else None,
                "memory_mode": overrides.memory_mode if overrides else None,
            }.items()
            if v is not None
        },
    )
    db.add(trace)
    db.flush()
    conversation.updated_at = datetime.now(conversation.updated_at.tzinfo)

    start = time.perf_counter()
    ttft_ms: int | None = None
    full_content = ""
    input_tokens = 0
    output_tokens = 0

    try:
        async for event in provider.stream(request):
            if event.type == "token":
                if ttft_ms is None:
                    ttft_ms = int((time.perf_counter() - start) * 1000)
                full_content += event.content
                db.add(
                    TraceEvent(
                        trace_id=trace.id,
                        event_type="token",
                        payload={"content": event.content},
                    )
                )
                yield StreamResult("token", {"content": event.content})
            elif event.type == "done":
                full_content = event.content or full_content
                input_tokens = event.input_tokens
                output_tokens = event.output_tokens
            elif event.type == "error":
                trace.errors = {
                    "code": event.error_code,
                    "message": event.error_message,
                }
                db.add(
                    TraceEvent(
                        trace_id=trace.id,
                        event_type="error",
                        payload={"code": event.error_code, "message": event.error_message},
                    )
                )
                yield StreamResult(
                    "error",
                    {"code": event.error_code, "message": event.error_message},
                )
                db.commit()
                return
    except Exception as exc:
        trace.errors = {"code": "runtime_error", "message": str(exc)}
        yield StreamResult("error", {"code": "runtime_error", "message": str(exc)})
        db.commit()
        return

    duration_ms = int((time.perf_counter() - start) * 1000)
    cost = estimate_cost(db, provider_name, model, input_tokens, output_tokens)

    assistant_msg.content = full_content
    trace.duration_ms = duration_ms
    trace.ttft_ms = ttft_ms
    trace.input_tokens = input_tokens
    trace.output_tokens = output_tokens
    trace.estimated_cost = cost

    db.add(
        TraceEvent(
            trace_id=trace.id,
            event_type="done",
            payload={
                "message_id": str(assistant_msg.id),
                "trace_id": str(trace.id),
            },
        )
    )
    db.commit()

    yield StreamResult(
        "done",
        {
            "message_id": str(assistant_msg.id),
            "trace_id": str(trace.id),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost": float(cost),
            "duration_ms": duration_ms,
            "ttft_ms": ttft_ms,
        },
    )


def get_user_conversation(
    db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> Conversation | None:
    return (
        db.query(Conversation)
        .join(Agent, Agent.id == Conversation.agent_id)
        .filter(Conversation.id == conversation_id, Agent.user_id == user_id)
        .first()
    )
