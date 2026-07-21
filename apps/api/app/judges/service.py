import asyncio
import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.judges.agreement import (
    estimate_judge_cost_per_case,
    mean_score,
    multi_judge_agreement,
    validate_and_normalize,
)
from app.judges.mock_payload import mock_judge_payload
from app.judges.prompt import build_judge_messages, parse_judge_json
from app.judges.rubrics import LIMITATIONS_NOTICE, STANDARD_SIX_CRITERIA
from app.judges.schemas import JudgeResultData, JudgeScoreResponse, MultiReviewResponse
from app.models.entities import (
    JudgeResult,
    JudgeRubricTemplate,
    JudgeRun,
    JudgeRunStatus,
    JudgeSourceType,
)
from app.providers.registry import get_judge_provider


def _criteria_dict(template: JudgeRubricTemplate | None) -> dict[str, Any]:
    if template and template.criteria:
        return dict(template.criteria)
    return dict(STANDARD_SIX_CRITERIA)


def _mock_judge_payload(
    criteria: dict[str, Any],
    assistant_answer: str,
    judge_index: int | None = None,
) -> dict:
    return mock_judge_payload(criteria, assistant_answer, judge_index)


async def _call_judge_llm(
    *,
    user_message: str,
    assistant_answer: str,
    criteria: dict[str, Any],
    expected_answer: str | None,
    judge_index: int | None,
    model: str | None,
) -> JudgeResultData:
    provider = get_judge_provider()
    judge_model = model or settings.judge_model or "mock-judge"
    messages = build_judge_messages(
        user_message=user_message,
        assistant_answer=assistant_answer,
        criteria=criteria,
        expected_answer=expected_answer,
        judge_index=judge_index,
    )

    from app.providers.base import ChatRequest

    if not settings.judge_api_key:
        raw = mock_judge_payload(criteria, assistant_answer, judge_index)
        validated = validate_and_normalize(raw, criteria)
        est = float(estimate_judge_cost_per_case())
        return JudgeResultData(
            criteria_scores={
                k: {"score": v.score, "explanation": v.explanation}
                for k, v in validated.criteria.items()
            },
            overall_score=validated.overall_score,
            passed=validated.passed,
            explanation=validated.explanation,
            evidence=validated.evidence,
            structured_raw=raw,
            input_tokens=100,
            output_tokens=80,
            estimated_cost=est,
        )

    response = await provider.complete(
        ChatRequest(model=judge_model, messages=messages, temperature=0.1, max_tokens=2048)
    )
    raw = parse_judge_json(response.content)
    validated = validate_and_normalize(raw, criteria)
    cost = float(estimate_judge_cost_per_case())

    return JudgeResultData(
        criteria_scores={
            k: {"score": v.score, "explanation": v.explanation}
            for k, v in validated.criteria.items()
        },
        overall_score=validated.overall_score,
        passed=validated.passed,
        explanation=validated.explanation,
        evidence=validated.evidence,
        structured_raw=raw,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        estimated_cost=cost,
    )


def run_judge_sync(
    *,
    user_message: str,
    assistant_answer: str,
    criteria: dict[str, Any],
    expected_answer: str | None = None,
    judge_index: int | None = None,
    model: str | None = None,
    min_overall: float | None = None,
) -> JudgeResultData:
    data = asyncio.run(
        _call_judge_llm(
            user_message=user_message,
            assistant_answer=assistant_answer,
            criteria=criteria,
            expected_answer=expected_answer,
            judge_index=judge_index,
            model=model,
        )
    )
    if min_overall is not None and data.overall_score < min_overall:
        data.passed = False
    return data


def persist_judge_result(
    db: Session,
    *,
    source_type: JudgeSourceType,
    source_id: uuid.UUID,
    rubric_template_id: uuid.UUID | None,
    data: JudgeResultData,
    evaluation_result_id: uuid.UUID | None = None,
    judge_index: int | None = None,
    model: str | None = None,
) -> tuple[JudgeRun, JudgeResult]:
    provider_name = "mock" if not settings.judge_api_key else "openai_compatible"
    run = JudgeRun(
        rubric_template_id=rubric_template_id,
        source_type=source_type,
        source_id=source_id,
        provider=provider_name,
        model=model or settings.judge_model or "mock-judge",
        status=JudgeRunStatus.completed,
        input_tokens=data.input_tokens,
        output_tokens=data.output_tokens,
        estimated_cost=Decimal(str(data.estimated_cost)),
        config_snapshot={"criteria_keys": list(data.criteria_scores.keys())},
    )
    db.add(run)
    db.flush()
    result = JudgeResult(
        judge_run_id=run.id,
        evaluation_result_id=evaluation_result_id,
        criteria_scores=data.criteria_scores,
        overall_score=Decimal(str(round(data.overall_score, 2))),
        passed=data.passed,
        explanation=data.explanation,
        evidence=data.evidence,
        structured_raw=data.structured_raw,
        judge_index=judge_index,
    )
    db.add(result)
    db.flush()
    return run, result


def judge_to_response(run: JudgeRun, result: JudgeResult) -> JudgeScoreResponse:
    return JudgeScoreResponse(
        judge_run_id=str(run.id),
        criteria_scores=result.criteria_scores or {},
        overall_score=float(result.overall_score or 0),
        passed=bool(result.passed),
        explanation=result.explanation or "",
        evidence=list(result.evidence or []),
        limitations_notice=LIMITATIONS_NOTICE,
    )


def run_multi_review_sync(
    db: Session,
    *,
    source_type: JudgeSourceType,
    source_id: uuid.UUID,
    user_message: str,
    assistant_answer: str,
    criteria: dict[str, Any],
    expected_answer: str | None,
    rubric_template_id: uuid.UUID | None,
    model: str | None,
) -> MultiReviewResponse:
    judges: list[JudgeScoreResponse] = []
    overalls: list[float] = []
    for idx in range(3):
        data = run_judge_sync(
            user_message=user_message,
            assistant_answer=assistant_answer,
            criteria=criteria,
            expected_answer=expected_answer,
            judge_index=idx,
            model=model,
        )
        run, result = persist_judge_result(
            db,
            source_type=JudgeSourceType.multi,
            source_id=source_id,
            rubric_template_id=rubric_template_id,
            data=data,
            judge_index=idx,
            model=model,
        )
        judges.append(judge_to_response(run, result))
        overalls.append(data.overall_score)

    agreement, disagreement = multi_judge_agreement(overalls)
    return MultiReviewResponse(
        judges=judges,
        agreement_percent=round(agreement, 1),
        mean_overall_score=round(mean_score(overalls), 2),
        disagreement=disagreement,
        limitations_notice=LIMITATIONS_NOTICE,
    )


def load_rubric_template(db: Session, template_id: uuid.UUID | None) -> JudgeRubricTemplate | None:
    if not template_id:
        return None
    return db.get(JudgeRubricTemplate, template_id)
