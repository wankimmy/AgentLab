import pytest

from app.judges.agreement import (
    compute_passed,
    mean_score,
    multi_judge_agreement,
    validate_and_normalize,
)


def test_validate_judge_schema():
    raw = {
        "criteria": {
            "correctness": {"score": 4, "explanation": "ok"},
            "relevance": {"score": 4, "explanation": "ok"},
        },
        "overall_score": 4,
        "passed": True,
        "explanation": "fine",
        "evidence": ["a"],
    }
    criteria = {
        "correctness": {"threshold": 3},
        "relevance": {"threshold": 3},
    }
    out = validate_and_normalize(raw, criteria)
    assert out.passed is True
    assert out.overall_score == 4.0


def test_compute_passed_threshold_failure():
    criteria = {"correctness": {"threshold": 4}}
    overall, passed = compute_passed(criteria, {"correctness": 3.5})
    assert passed is False
    assert overall == 3.5


def test_multi_judge_agreement():
    agreement, disagreement = multi_judge_agreement([4.0, 4.2, 4.1])
    assert agreement > 90
    assert disagreement is False

    agreement2, disagreement2 = multi_judge_agreement([2.0, 4.5, 4.0])
    assert disagreement2 is True
    assert mean_score([2.0, 4.5, 4.0]) == pytest.approx(3.5)
