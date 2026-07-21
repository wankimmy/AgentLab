import uuid
from collections.abc import AsyncIterator
from typing import Protocol

from sqlalchemy.orm import Session

from app.models.entities import AgentVersion, Conversation
from app.services.turn_models import StreamResult, TurnOverrides


class RuntimeAdapter(Protocol):
    async def stream_turn(
        self,
        db: Session,
        conversation: Conversation,
        version: AgentVersion,
        user_content: str,
        overrides: TurnOverrides | None,
        user_id: uuid.UUID,
    ) -> AsyncIterator[StreamResult]: ...
