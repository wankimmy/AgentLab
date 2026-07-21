"""Non-tool chat turn streaming (native runtime path without tools)."""

import time
from collections.abc import AsyncIterator
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.entities import (
    AgentVersion,
    AgentVersionCollection,
    ChatTrace,
    Conversation,
    Message,
    MessageRole,
    TraceEvent,
)
from app.providers.base import ChatRequest
from app.providers.registry import get_provider
from app.services.turn_models import StreamResult, TurnOverrides, assemble_messages
from app.services.cost_service import estimate_cost
from app.services.retrieval_service import RetrievalService, build_rag_context_block


async def stream_simple_turn(
    db: Session,
    conversation: Conversation,
    version: AgentVersion,
    user_content: str,
    overrides: TurnOverrides | None,
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

    retrieved_citations: list[dict] = []
    if version.rag_enabled:
        linked = (
            db.query(AgentVersionCollection)
            .filter(AgentVersionCollection.agent_version_id == version.id)
            .count()
        )
        if linked > 0:
            from app.observability.otel import span_retrieval_search

            with span_retrieval_search(
                version_id=str(version.id),
                top_k=int((version.retrieval_config or {}).get("top_k", 5)),
                mode=str((version.retrieval_config or {}).get("mode", "hybrid")),
            ):
                chunks = RetrievalService(db).retrieve(
                    user_content,
                    version_id=version.id,
                    config=version.retrieval_config,
                )
            retrieved_citations = [c.to_citation() for c in chunks]
            rag_block = build_rag_context_block(chunks)
            if rag_block:
                messages.insert(1, {"role": "system", "content": rag_block})

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
        retrieved_chunks=retrieved_citations,
    )
    db.add(trace)
    db.flush()
    conversation.updated_at = datetime.now(conversation.updated_at.tzinfo)

    start = time.perf_counter()
    ttft_ms: int | None = None
    full_content = ""
    input_tokens = 0
    output_tokens = 0

    from app.observability.otel import span_agent_turn, span_provider_chat

    try:
        with span_agent_turn(
            agent_version_id=str(version.id),
            model=model,
            runtime=version.runtime_type.value,
        ):
            with span_provider_chat(provider=provider_name, model=model):
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
                                payload={
                                    "code": event.error_code,
                                    "message": event.error_message,
                                },
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
