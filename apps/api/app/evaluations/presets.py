"""Eight evaluation metric presets from template-design §8."""

from typing import Any

EVAL_PRESETS: list[dict[str, Any]] = [
    {
        "id": "customer_support_quality",
        "name": "Customer Support Quality",
        "description": "Keyword coverage, forbidden terms, and semantic relevance.",
        "metrics": [
            "response_exists",
            "required_keyword",
            "forbidden_keyword",
            "semantic_similarity",
        ],
        "quick_metrics": ["response_exists", "required_keyword", "forbidden_keyword"],
        "thresholds": {"semantic_similarity": 0.8, "pass_rate": 0.85},
    },
    {
        "id": "rag_accuracy",
        "name": "RAG Accuracy",
        "description": "Retrieval, citation, and grounded answer checks.",
        "metrics": [
            "response_exists",
            "expected_source_retrieved",
            "citation_present",
            "citation_correctness",
            "answer_support",
            "semantic_similarity",
        ],
        "quick_metrics": [
            "response_exists",
            "expected_source_retrieved",
            "citation_present",
        ],
        "thresholds": {"semantic_similarity": 0.8, "pass_rate": 0.9},
    },
    {
        "id": "tool_calling_accuracy",
        "name": "Tool-Calling Accuracy",
        "description": "Expected tool invocation and argument matching.",
        "metrics": [
            "response_exists",
            "expected_tool",
            "expected_tool_args",
            "tool_execution_success",
        ],
        "quick_metrics": ["expected_tool", "tool_execution_success"],
        "thresholds": {"pass_rate": 0.95},
    },
    {
        "id": "safety_and_refusal",
        "name": "Safety and Refusal",
        "description": "Refusal behaviour, forbidden keywords, and security cases.",
        "metrics": [
            "response_exists",
            "forbidden_keyword",
            "forbidden_claim",
            "refusal_expected",
            "refusal_not_expected",
        ],
        "quick_metrics": ["forbidden_keyword", "refusal_expected"],
        "thresholds": {"pass_rate": 1.0},
    },
    {
        "id": "structured_data_extraction",
        "name": "Structured Data Extraction",
        "description": "JSON schema validation and exact match extraction.",
        "metrics": ["response_exists", "structured_schema", "exact_match"],
        "quick_metrics": ["structured_schema", "exact_match"],
        "thresholds": {"pass_rate": 0.9},
    },
    {
        "id": "policy_compliance",
        "name": "Policy Compliance",
        "description": "Retrieval, refusal, and citation for policy-bound agents.",
        "metrics": [
            "response_exists",
            "expected_source_retrieved",
            "refusal_expected",
            "citation_present",
            "forbidden_claim",
        ],
        "quick_metrics": ["refusal_expected", "forbidden_claim", "citation_present"],
        "thresholds": {"pass_rate": 0.95},
    },
    {
        "id": "developer_documentation",
        "name": "Developer Documentation",
        "description": "Keyword, semantic, and citation checks for doc assistants.",
        "metrics": [
            "response_exists",
            "required_keyword",
            "semantic_similarity",
            "citation_present",
        ],
        "quick_metrics": ["required_keyword", "response_exists"],
        "thresholds": {"semantic_similarity": 0.8, "pass_rate": 0.85},
    },
    {
        "id": "release_readiness",
        "name": "Release Readiness",
        "description": "Broad metric sweep for release gating (no judge in Phase 6).",
        "metrics": [
            "response_exists",
            "required_keyword",
            "forbidden_keyword",
            "expected_tool",
            "tool_execution_success",
            "expected_source_retrieved",
            "citation_correctness",
            "latency_threshold",
            "token_threshold",
            "semantic_similarity",
        ],
        "quick_metrics": [
            "response_exists",
            "required_keyword",
            "forbidden_keyword",
            "expected_tool",
        ],
        "thresholds": {"semantic_similarity": 0.8, "pass_rate": 0.9},
    },
]


def get_preset(preset_id: str) -> dict[str, Any] | None:
    return next((p for p in EVAL_PRESETS if p["id"] == preset_id), None)
