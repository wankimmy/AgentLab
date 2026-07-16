from dataclasses import dataclass, field
from decimal import Decimal

from app.models.entities import EvaluationCase, MetricType


@dataclass
class CaseInput:
    name: str
    category: str = ""
    user_message: str = ""
    expected_answer: str | None = None
    expected_behaviour: str | None = None
    required_keywords: list[str] = field(default_factory=list)
    forbidden_keywords: list[str] = field(default_factory=list)
    forbidden_claims: list[str] = field(default_factory=list)
    expected_source: str | None = None
    expected_citation: str | None = None
    expected_tool: str | None = None
    expected_tool_args: dict | None = None
    max_latency_ms: int | None = None
    max_tokens: int | None = None
    max_cost: Decimal | None = None
    severity: str = "medium"
    conversation_history: list[dict] | None = None

    @classmethod
    def from_entity(cls, case: EvaluationCase) -> "CaseInput":
        history = case.conversation_history
        hist_list: list[dict] | None = None
        if isinstance(history, list):
            hist_list = history
        elif isinstance(history, dict) and "messages" in history:
            hist_list = history["messages"]
        return cls(
            name=case.name,
            category=case.category,
            user_message=case.user_message,
            expected_answer=case.expected_answer,
            expected_behaviour=case.expected_behaviour,
            required_keywords=list(case.required_keywords or []),
            forbidden_keywords=list(case.forbidden_keywords or []),
            forbidden_claims=list(case.forbidden_claims or []),
            expected_source=case.expected_source,
            expected_citation=case.expected_citation,
            expected_tool=case.expected_tool,
            expected_tool_args=case.expected_tool_args,
            max_latency_ms=case.max_latency_ms,
            max_tokens=case.max_tokens,
            max_cost=case.max_cost,
            severity=case.severity.value if hasattr(case.severity, "value") else str(case.severity),
            conversation_history=hist_list,
        )


@dataclass
class TraceSnapshot:
    duration_ms: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost: Decimal = Decimal("0")
    retrieved_chunks: list = field(default_factory=list)
    tool_requests: list = field(default_factory=list)
    tool_results: list = field(default_factory=list)
    errors: dict | None = None

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class MetricOutcome:
    metric_name: str
    metric_type: MetricType
    passed: bool
    score: float | None = None
    threshold: float | None = None
    details: dict | None = None
