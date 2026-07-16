import csv
import io
import json
from typing import Any

from app.evaluations.schemas import CaseCreate
from app.models.entities import EvaluationCase

CASE_FIELDS = [
    "name",
    "category",
    "user_message",
    "expected_answer",
    "expected_behaviour",
    "required_keywords",
    "forbidden_keywords",
    "forbidden_claims",
    "expected_source",
    "expected_citation",
    "expected_tool",
    "severity",
]


def _split_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split("|") if part.strip()]


def parse_cases_json(payload: bytes) -> list[CaseCreate]:
    data = json.loads(payload.decode("utf-8"))
    if isinstance(data, dict) and "cases" in data:
        rows = data["cases"]
    elif isinstance(data, list):
        rows = data
    else:
        raise ValueError("JSON must be a list of cases or {cases: [...]}")
    return [CaseCreate.model_validate(row) for row in rows]


def parse_cases_csv(payload: bytes) -> list[CaseCreate]:
    text = payload.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    cases: list[CaseCreate] = []
    for row in reader:
        cases.append(
            CaseCreate(
                name=row.get("name", "Unnamed"),
                category=row.get("category", ""),
                user_message=row.get("user_message", ""),
                expected_answer=row.get("expected_answer") or None,
                expected_behaviour=row.get("expected_behaviour") or None,
                required_keywords=_split_list(row.get("required_keywords")),
                forbidden_keywords=_split_list(row.get("forbidden_keywords")),
                forbidden_claims=_split_list(row.get("forbidden_claims")),
                expected_source=row.get("expected_source") or None,
                expected_citation=row.get("expected_citation") or None,
                expected_tool=row.get("expected_tool") or None,
            )
        )
    return cases


def case_to_dict(case: EvaluationCase) -> dict[str, Any]:
    return {
        "name": case.name,
        "category": case.category,
        "user_message": case.user_message,
        "expected_answer": case.expected_answer,
        "expected_behaviour": case.expected_behaviour,
        "required_keywords": list(case.required_keywords or []),
        "forbidden_keywords": list(case.forbidden_keywords or []),
        "forbidden_claims": list(case.forbidden_claims or []),
        "expected_source": case.expected_source,
        "expected_citation": case.expected_citation,
        "expected_tool": case.expected_tool,
        "expected_tool_args": case.expected_tool_args,
        "max_latency_ms": case.max_latency_ms,
        "max_tokens": case.max_tokens,
        "severity": case.severity.value,
        "tags": list(case.tags or []),
        "notes": case.notes,
    }


def export_cases_json(cases: list[EvaluationCase]) -> bytes:
    payload = {"cases": [case_to_dict(c) for c in cases]}
    return json.dumps(payload, indent=2).encode("utf-8")


def export_cases_csv(cases: list[EvaluationCase]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CASE_FIELDS)
    writer.writeheader()
    for case in cases:
        writer.writerow(
            {
                "name": case.name,
                "category": case.category,
                "user_message": case.user_message,
                "expected_answer": case.expected_answer or "",
                "expected_behaviour": case.expected_behaviour or "",
                "required_keywords": "|".join(case.required_keywords or []),
                "forbidden_keywords": "|".join(case.forbidden_keywords or []),
                "forbidden_claims": "|".join(case.forbidden_claims or []),
                "expected_source": case.expected_source or "",
                "expected_citation": case.expected_citation or "",
                "expected_tool": case.expected_tool or "",
                "severity": case.severity.value,
            }
        )
    return buffer.getvalue().encode("utf-8")
