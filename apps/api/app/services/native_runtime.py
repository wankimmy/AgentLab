import asyncio
import json
import time
import uuid
from collections.abc import AsyncIterator
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.entities import (
    Agent,
    AgentVersion,
    AgentVersionCollection,
    ChatTrace,
    Conversation,
    Message,
    MessageRole,
    ToolApproval,
    ToolApprovalStatus,
    ToolMode,
    TraceEvent,
)
from app.providers.base import ChatRequest
from app.providers.registry import get_provider
from app.services.turn_models import StreamResult, TurnOverrides, assemble_messages
from app.services.cost_service import estimate_cost
from app.services.retrieval_service import RetrievalService, build_rag_context_block
from app.tools.executor import ToolContext, ToolExecutionError, execute_tool, tool_result_content
from app.tools.registry import (
    build_tool_schemas,
    get_runtime_limits,
    get_tool_mode,
)


async def _wait_for_approval(
    db: Session,
    approval_id: uuid.UUID,
    timeout_seconds: int,
) -> ToolApprovalStatus:
    deadline = time.perf_counter() + timeout_seconds
    while time.perf_counter() < deadline:
        db.expire_all()
        approval = db.get(ToolApproval, approval_id)
        if not approval:
            return ToolApprovalStatus.expired
        if approval.status != ToolApprovalStatus.pending:
            return approval.status
        await asyncio.sleep(0.25)
    approval = db.get(ToolApproval, approval_id)
    if approval and approval.status == ToolApprovalStatus.pending:
        approval.status = ToolApprovalStatus.expired
        db.flush()
    return ToolApprovalStatus.expired


async def stream_native_turn(
    db: Session,
    conversation: Conversation,
    version: AgentVersion,
    user_content: str,
    overrides: TurnOverrides | None,
    user_id: uuid.UUID,
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
    limits = get_runtime_limits(version.tool_config or {})
    tool_schemas = build_tool_schemas(db, version)

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
        tool_requests=[],
        tool_results=[],
        guardrail_results=[],
    )
    db.add(trace)
    db.flush()
    conversation.updated_at = datetime.now(conversation.updated_at.tzinfo)

    provider = get_provider(provider_name)
    ctx = ToolContext(
        db=db,
        version=version,
        conversation=conversation,
        trace_id=trace.id,
        user_id=user_id,
    )

    start = time.perf_counter()
    ttft_ms: int | None = None
    full_content = ""
    input_tokens = 0
    output_tokens = 0
    tool_requests: list[dict] = []
    tool_results: list[dict] = []
    guardrail_results: list[dict] = []
    agent_steps = 0
    tool_call_count = 0
    loop_messages = list(messages)

    try:
        while agent_steps < limits["max_agent_steps"]:
            agent_steps += 1
            request = ChatRequest(
                model=model,
                messages=loop_messages,
                temperature=float(temperature),
                max_tokens=int(max_tokens),
                tools=tool_schemas or None,
            )

            pending_tool_calls: list[dict] = []
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
                elif event.type == "tool_calls":
                    pending_tool_calls = event.metadata.get("tool_calls", [])
                elif event.type == "done":
                    full_content = event.content or full_content
                    input_tokens += event.input_tokens
                    output_tokens += event.output_tokens
                elif event.type == "error":
                    trace.errors = {
                        "code": event.error_code,
                        "message": event.error_message,
                    }
                    yield StreamResult(
                        "error",
                        {"code": event.error_code, "message": event.error_message},
                    )
                    db.commit()
                    return

            if not pending_tool_calls:
                break

            assistant_tool_calls = []
            for call in pending_tool_calls:
                tool_call_count += 1
                if tool_call_count > limits["max_tool_calls"]:
                    guardrail_results.append(
                        {"type": "max_tool_calls", "limit": limits["max_tool_calls"]}
                    )
                    yield StreamResult(
                        "error",
                        {
                            "code": "tool_limit",
                            "message": "Maximum tool calls reached",
                        },
                    )
                    trace.guardrail_results = guardrail_results
                    db.commit()
                    return

                tool_name = call["name"]
                arguments = call.get("arguments") or {}
                tool_call_id = call.get("id") or f"call_{uuid.uuid4().hex[:8]}"
                mode = get_tool_mode(version.tool_config or {}, tool_name)
                call_meta = {
                    "id": tool_call_id,
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "arguments": json.dumps(arguments),
                    },
                }
                assistant_tool_calls.append(call_meta)

                req_record = {
                    "tool": tool_name,
                    "arguments": arguments,
                    "tool_call_id": tool_call_id,
                }
                tool_requests.append(req_record)
                yield StreamResult(
                    "tool_call",
                    {"tool": tool_name, "arguments": arguments, "tool_call_id": tool_call_id},
                )

                if mode == ToolMode.disabled:
                    result_text = json.dumps({"error": "Tool disabled"})
                    tool_results.append(
                        {"tool": tool_name, "status": "disabled", "output": result_text}
                    )
                    yield StreamResult(
                        "tool_result",
                        {"tool": tool_name, "status": "disabled", "output": result_text},
                    )
                    loop_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call_id,
                            "content": result_text,
                        }
                    )
                    continue

                approved = mode == ToolMode.auto
                if mode == ToolMode.approval:
                    approval = ToolApproval(
                        conversation_id=conversation.id,
                        message_id=assistant_msg.id,
                        trace_id=trace.id,
                        tool_name=tool_name,
                        tool_call_id=tool_call_id,
                        arguments=arguments,
                    )
                    db.add(approval)
                    db.flush()
                    yield StreamResult(
                        "approval_required",
                        {
                            "approval_id": str(approval.id),
                            "tool": tool_name,
                            "arguments": arguments,
                            "reason": "Tool requires manual approval per agent configuration",
                        },
                    )
                    decision = await _wait_for_approval(db, approval.id, limits["timeout_seconds"])
                    approved = decision == ToolApprovalStatus.approved
                    if decision == ToolApprovalStatus.rejected:
                        result_text = json.dumps({"error": "Tool call rejected by user"})
                        tool_results.append(
                            {"tool": tool_name, "status": "rejected", "output": result_text}
                        )
                        yield StreamResult(
                            "tool_result",
                            {"tool": tool_name, "status": "rejected", "output": result_text},
                        )
                        loop_messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call_id,
                                "content": result_text,
                            }
                        )
                        continue
                    if not approved:
                        yield StreamResult(
                            "error",
                            {
                                "code": "approval_timeout",
                                "message": "Tool approval timed out",
                            },
                        )
                        trace.errors = {
                            "code": "approval_timeout",
                            "message": "Tool approval timed out",
                        }
                        db.commit()
                        return

                try:
                    from app.observability.otel import span_tool_execute

                    with span_tool_execute(tool_name=tool_name):
                        output = execute_tool(ctx, tool_name, arguments)
                    result_text = tool_result_content(output)
                    tool_results.append({"tool": tool_name, "status": "success", "output": output})
                    yield StreamResult(
                        "tool_result",
                        {"tool": tool_name, "status": "success", "output": output},
                    )
                except ToolExecutionError as exc:
                    result_text = json.dumps({"error": str(exc)})
                    tool_results.append({"tool": tool_name, "status": "error", "output": str(exc)})
                    yield StreamResult(
                        "tool_result",
                        {"tool": tool_name, "status": "error", "output": str(exc)},
                    )

                loop_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": result_text,
                    }
                )

            if pending_tool_calls:
                loop_messages.append(
                    {
                        "role": "assistant",
                        "content": full_content or "",
                        "tool_calls": assistant_tool_calls,
                    }
                )
                full_content = ""
                continue
            break
        else:
            guardrail_results.append(
                {"type": "max_agent_steps", "limit": limits["max_agent_steps"]}
            )
            yield StreamResult(
                "error",
                {"code": "step_limit", "message": "Maximum agent steps reached"},
            )
            trace.guardrail_results = guardrail_results
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
    trace.tool_requests = tool_requests
    trace.tool_results = tool_results
    trace.guardrail_results = guardrail_results

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


def resolve_user_id(db: Session, conversation: Conversation) -> uuid.UUID:
    agent = db.get(Agent, conversation.agent_id)
    if not agent:
        raise ValueError("Agent not found")
    return agent.user_id
