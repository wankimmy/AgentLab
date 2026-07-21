import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.models.entities import Agent, AgentVersion, Conversation, Message, MessageRole

router = APIRouter(prefix="/reviews", tags=["reviews"])


class BlindAbCreate(BaseModel):
    left_message_id: uuid.UUID
    right_message_id: uuid.UUID
    preference: str = Field(pattern="^(left|right)$")


class BlindAbResponse(BaseModel):
    id: uuid.UUID
    preference: str
    revealed_labels: dict[str, str]


def _owned_message(db: Session, message_id: uuid.UUID, user_id: uuid.UUID) -> Message:
    message = db.get(Message, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    conv = db.get(Conversation, message.conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Message not found")
    agent = db.get(Agent, conv.agent_id)
    if not agent or agent.user_id != user_id:
        raise HTTPException(status_code=404, detail="Message not found")
    return message


def _message_label(db: Session, message: Message) -> str:
    conv = db.get(Conversation, message.conversation_id)
    if not conv or not conv.agent_version_id:
        return "Unknown version"
    version = db.get(AgentVersion, conv.agent_version_id)
    if not version:
        return "Unknown version"
    return f"Version {version.version_number}"


@router.post("/blind-ab", response_model=BlindAbResponse)
def submit_blind_ab(
    body: BlindAbCreate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> BlindAbResponse:
    left = _owned_message(db, body.left_message_id, user.id)
    right = _owned_message(db, body.right_message_id, user.id)
    if left.role != MessageRole.assistant or right.role != MessageRole.assistant:
        raise HTTPException(status_code=400, detail="Both messages must be assistant responses")

    left_label = _message_label(db, left)
    right_label = _message_label(db, right)

    from app.models.entities import BlindAbReview

    review = BlindAbReview(
        reviewer_user_id=user.id,
        left_message_id=left.id,
        right_message_id=right.id,
        left_label=left_label,
        right_label=right_label,
        preference=body.preference,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    return BlindAbResponse(
        id=review.id,
        preference=review.preference,
        revealed_labels={"left": left_label, "right": right_label},
    )
