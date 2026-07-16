import asyncio
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.entities import (
    Agent,
    AgentVersion,
    ChatTrace,
    Conversation,
    Message,
    MessageRole,
)
from app.services.chat_runtime import stream_chat_turn


@dataclass
class EvalTurnResult:
    actual_answer: str
    trace_id: uuid.UUID | None
    error: str | None = None


async def _collect_turn(
    db: Session,
    conversation: Conversation,
    version: AgentVersion,
    user_message: str,
) -> EvalTurnResult:
    content = ""
    trace_id: uuid.UUID | None = None
    error: str | None = None

    async for result in stream_chat_turn(db, conversation, version, user_message, None):
        if result.event_type == "token":
            content += result.data.get("content", "")
        elif result.event_type == "done":
            trace_id_raw = result.data.get("trace_id")
            if trace_id_raw:
                trace_id = uuid.UUID(str(trace_id_raw))
        elif result.event_type == "error":
            error = result.data.get("message", "runtime error")
            return EvalTurnResult(actual_answer=content, trace_id=trace_id, error=error)

    if not content and trace_id:
        assistant = (
            db.query(Message)
            .join(ChatTrace, ChatTrace.message_id == Message.id)
            .filter(ChatTrace.id == trace_id)
            .first()
        )
        if assistant:
            content = assistant.content

    return EvalTurnResult(actual_answer=content, trace_id=trace_id, error=error)


def _seed_history(
    db: Session,
    conversation: Conversation,
    history: list[dict] | None,
) -> None:
    if not history:
        return
    for idx, item in enumerate(history):
        role_raw = item.get("role", "user")
        try:
            role = MessageRole(role_raw)
        except ValueError:
            role = MessageRole.user
        db.add(
            Message(
                conversation_id=conversation.id,
                role=role,
                content=str(item.get("content", "")),
                sequence=idx,
            )
        )
    db.flush()


def run_eval_turn(
    db: Session,
    agent_version: AgentVersion,
    user_id: uuid.UUID,
    user_message: str,
    *,
    conversation_history: list[dict] | None = None,
) -> EvalTurnResult:
    agent = db.get(Agent, agent_version.agent_id)
    if not agent or agent.user_id != user_id:
        return EvalTurnResult(actual_answer="", trace_id=None, error="Agent not found")

    conversation = Conversation(
        agent_id=agent.id,
        agent_version_id=agent_version.id,
        title="Evaluation run",
    )
    db.add(conversation)
    db.flush()
    _seed_history(db, conversation, conversation_history)
    conversation.updated_at = datetime.now(UTC)

    return asyncio.run(_collect_turn(db, conversation, agent_version, user_message))
