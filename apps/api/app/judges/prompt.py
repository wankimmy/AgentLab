import json
from typing import Any


def build_judge_messages(
    *,
    user_message: str,
    assistant_answer: str,
    criteria: dict[str, Any],
    expected_answer: str | None = None,
    judge_index: int | None = None,
) -> list[dict[str, str]]:
    criteria_lines = []
    for name, cfg in criteria.items():
        threshold = cfg.get("threshold", 3)
        criteria_lines.append(f"- {name}: score 1-5 (pass threshold {threshold})")

    expected_block = ""
    if expected_answer:
        expected_block = f"\nReference expected answer (if applicable):\n{expected_answer}\n"

    index_note = ""
    if judge_index is not None:
        index_note = f"\nYou are judge #{judge_index + 1} of 3. Apply consistent scoring.\n"

    system = (
        "You are an LLM judge for agent quality evaluation. "
        "Score the assistant response using the rubric. "
        "Respond with JSON only, no markdown fences."
        f"{index_note}\n"
        "Required JSON shape:\n"
        '{"criteria": {"<name>": {"score": number, "explanation": string}, ...}, '
        '"overall_score": number, "passed": boolean, "explanation": string, '
        '"evidence": [string, ...]}\n\n'
        "Rubric criteria:\n" + "\n".join(criteria_lines)
    )

    user = (
        f"User message:\n{user_message}\n\n"
        f"Assistant answer:\n{assistant_answer}\n"
        f"{expected_block}\n"
        "Return valid JSON matching the schema."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_judge_json(content: str) -> dict:
    text = content.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)
