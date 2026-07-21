import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.authentication.router import CurrentUser
from app.core.db import get_db
from app.judges.schemas import MultiReviewRequest, MultiReviewResponse, RubricTemplateResponse
from app.judges.service import (
    _criteria_dict,
    load_rubric_template,
    run_multi_review_sync,
)
from app.models.entities import (
    Agent,
    AgentVersion,
    Conversation,
    EvaluationCase,
    EvaluationResult,
    EvaluationRun,
    JudgeRubricTemplate,
    JudgeSourceType,
    Message,
    MessageRole,
)

router = APIRouter(prefix="/judges", tags=["judges"])


@router.get("/rubrics", response_model=list[RubricTemplateResponse])
def list_rubrics(user: CurrentUser, db: Session = Depends(get_db)) -> list[RubricTemplateResponse]:
    del user
    templates = db.query(JudgeRubricTemplate).order_by(JudgeRubricTemplate.name.asc()).all()
    return [
        RubricTemplateResponse(
            id=str(t.id),
            name=t.name,
            description=t.description,
            criteria=t.criteria or {},
            version=t.version,
        )
        for t in templates
    ]


@router.post("/multi-review", response_model=MultiReviewResponse)
def multi_review(
    body: MultiReviewRequest,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> MultiReviewResponse:
    user_message = body.user_message
    assistant_answer = body.assistant_answer
    expected_answer = body.expected_answer
    source_id: uuid.UUID
    source_type = JudgeSourceType.multi

    rubric_id = uuid.UUID(body.rubric_template_id) if body.rubric_template_id else None
    template = load_rubric_template(db, rubric_id)
    criteria = _criteria_dict(template)

    if body.message_id:
        message = db.get(Message, uuid.UUID(body.message_id))
        if not message or message.role != MessageRole.assistant:
            raise HTTPException(status_code=404, detail="Assistant message not found")
        conv = db.get(Conversation, message.conversation_id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        agent = db.get(Agent, conv.agent_id)
        if not agent or agent.user_id != user.id:
            raise HTTPException(status_code=404, detail="Message not found")
        assistant_answer = message.content
        prior = (
            db.query(Message)
            .filter(
                Message.conversation_id == conv.id,
                Message.created_at < message.created_at,
                Message.role == MessageRole.user,
            )
            .order_by(Message.created_at.desc())
            .first()
        )
        user_message = prior.content if prior else ""
        source_id = message.id
        source_type = JudgeSourceType.message
    elif body.evaluation_result_id:
        result = (
            db.query(EvaluationResult)
            .join(EvaluationRun, EvaluationRun.id == EvaluationResult.run_id)
            .join(AgentVersion, AgentVersion.id == EvaluationRun.agent_version_id)
            .join(Agent, Agent.id == AgentVersion.agent_id)
            .filter(
                EvaluationResult.id == uuid.UUID(body.evaluation_result_id),
                Agent.user_id == user.id,
            )
            .first()
        )
        if not result:
            raise HTTPException(status_code=404, detail="Result not found")
        case = db.get(EvaluationCase, result.case_id)
        user_message = case.user_message if case else ""
        assistant_answer = result.actual_answer
        expected_answer = case.expected_answer if case else expected_answer
        source_id = result.id
        source_type = JudgeSourceType.evaluation_result
    else:
        if not user_message or not assistant_answer:
            raise HTTPException(
                status_code=400,
                detail="Provide message_id, evaluation_result_id, or user_message+assistant_answer",
            )
        source_id = uuid.uuid4()

    if not assistant_answer:
        raise HTTPException(status_code=400, detail="No assistant answer to judge")

    response = run_multi_review_sync(
        db,
        source_type=source_type,
        source_id=source_id,
        user_message=user_message,
        assistant_answer=assistant_answer,
        criteria=criteria,
        expected_answer=expected_answer,
        rubric_template_id=rubric_id,
        model=None,
    )
    db.commit()
    return response
