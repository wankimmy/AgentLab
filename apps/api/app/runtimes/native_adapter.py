import uuid
from collections.abc import AsyncIterator

from sqlalchemy.orm import Session

from app.models.entities import AgentVersion, Conversation
from app.services.turn_models import StreamResult, TurnOverrides
from app.services.native_runtime import resolve_user_id, stream_native_turn
from app.runtimes.simple_turn import stream_simple_turn
from app.tools.registry import has_enabled_tools


class NativeRuntimeAdapter:
    async def stream_turn(
        self,
        db: Session,
        conversation: Conversation,
        version: AgentVersion,
        user_content: str,
        overrides: TurnOverrides | None,
        user_id: uuid.UUID,
    ) -> AsyncIterator[StreamResult]:
        if has_enabled_tools(version):
            async for result in stream_native_turn(
                db, conversation, version, user_content, overrides, user_id
            ):
                yield result
            return
        async for result in stream_simple_turn(
            db, conversation, version, user_content, overrides
        ):
            yield result

    @staticmethod
    def resolve_user_id(db: Session, conversation: Conversation) -> uuid.UUID:
        return resolve_user_id(db, conversation)
