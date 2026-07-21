"""Built-in rubric criteria for LLM judge."""

STANDARD_SIX_CRITERIA: dict[str, dict[str, int | str]] = {
    "correctness": {"scale": "1-5", "threshold": 3},
    "relevance": {"scale": "1-5", "threshold": 3},
    "completeness": {"scale": "1-5", "threshold": 3},
    "groundedness": {"scale": "1-5", "threshold": 3},
    "instruction_following": {"scale": "1-5", "threshold": 3},
    "clarity": {"scale": "1-5", "threshold": 3},
}

LIMITATIONS_NOTICE = (
    "Judge results are probabilistic and may vary between runs. "
    "They do not replace deterministic tests or human review for critical cases."
)

MAX_JUDGE_CALLS_PER_RUN = 100

SYSTEM_RUBRIC_TEMPLATES: list[dict] = [
    {
        "name": "Standard Six Criteria",
        "description": (
            "Correctness, relevance, completeness, groundedness, instruction following, clarity."
        ),
        "criteria": STANDARD_SIX_CRITERIA,
    },
    {
        "name": "ERP Support Rubric",
        "description": "ERP-focused rubric with citation emphasis.",
        "criteria": {
            **STANDARD_SIX_CRITERIA,
            "citation": {"scale": "1-5", "threshold": 4},
        },
    },
]
