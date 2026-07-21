from pydantic import BaseModel, Field


class CriterionScore(BaseModel):
    score: float = Field(ge=1, le=5)
    explanation: str = ""


class JudgeOutputSchema(BaseModel):
    criteria: dict[str, CriterionScore]
    overall_score: float = Field(ge=1, le=5)
    passed: bool
    explanation: str = ""
    evidence: list[str] = Field(default_factory=list)


class JudgeResultData(BaseModel):
    criteria_scores: dict[str, dict[str, str | float]]
    overall_score: float
    passed: bool
    explanation: str
    evidence: list[str]
    structured_raw: dict
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: float = 0.0


class RubricTemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    criteria: dict
    version: int


class MultiReviewRequest(BaseModel):
    message_id: str | None = None
    evaluation_result_id: str | None = None
    rubric_template_id: str | None = None
    user_message: str | None = None
    assistant_answer: str | None = None
    expected_answer: str | None = None


class JudgeScoreResponse(BaseModel):
    judge_run_id: str
    criteria_scores: dict
    overall_score: float
    passed: bool
    explanation: str
    evidence: list[str]
    limitations_notice: str


class MultiReviewResponse(BaseModel):
    judges: list[JudgeScoreResponse]
    agreement_percent: float
    mean_overall_score: float
    disagreement: bool
    limitations_notice: str


class MessageJudgeRequest(BaseModel):
    rubric_template_id: str | None = None
    expected_answer: str | None = None
