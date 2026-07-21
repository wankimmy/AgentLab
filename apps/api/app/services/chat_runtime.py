import uuid
from collections.abc import AsyncIterator

from sqlalchemy.orm import Session

from app.models.entities import Agent, AgentVersion, Conversation
from app.runtimes.native_adapter import NativeRuntimeAdapter
from app.runtimes.registry import get_runtime_adapter
from app.services.turn_models import StreamResult, TurnOverrides, regenerate_summary_stub, assemble_messages

# Re-export for backward compatibility
__all__ = [
    "TurnOverrides",
    "StreamResult",
    "assemble_messages",
    "regenerate_summary_stub",
    "stream_chat_turn",
    "get_user_conversation",
]


async def stream_chat_turn(
    db: Session,
    conversation: Conversation,
    version: AgentVersion,
    user_content: str,
    overrides: TurnOverrides | None = None,
) -> AsyncIterator[StreamResult]:
    adapter = get_runtime_adapter(version.runtime_type)
    user_id = NativeRuntimeAdapter.resolve_user_id(db, conversation)
    async for result in adapter.stream_turn(
        db, conversation, version, user_content, overrides, user_id
    ):
        yield result


def get_user_conversation(
    db: Session, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> Conversation | None:
    return (
        db.query(Conversation)
        .join(Agent, Agent.id == Conversation.agent_id)
        .filter(Conversation.id == conversation_id, Agent.user_id == user_id)
        .first()
    )
