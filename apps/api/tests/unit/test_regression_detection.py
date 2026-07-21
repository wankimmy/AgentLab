from app.comparisons.engine import compare_eval_runs
from app.comparisons.regression import evaluate_thresholds
from app.models.entities import CaseClassification, CaseSeverity, ReleaseCheckStatus


def test_newly_failed_case_is_regression():
    from types import SimpleNamespace

    base_result = SimpleNamespace(overall_pass=True, latency_ms=100, cost=0)
    cand_result = SimpleNamespace(overall_pass=False, latency_ms=120, cost=0)
    case = SimpleNamespace(
        id="c1",
        name="case-1",
        severity=CaseSeverity.medium,
        category="correct",
    )
    rows, base_rate, cand_rate = compare_eval_runs(
        baseline_results=[(base_result, case, [])],
        candidate_by_case={"c1": (cand_result, [])},
    )
    assert len(rows) == 1
    assert rows[0].classification == CaseClassification.regressed
    assert base_rate == 1.0
    assert cand_rate == 0.0


def test_threshold_blocks_critical_failures():
    status, findings = evaluate_thresholds(
        pass_rate=0.95,
        rules={"pass_rate": 0.9, "critical_pass_rate": 1.0},
        regressions=[],
        critical_failures=1,
        security_failures=0,
    )
    assert status == ReleaseCheckStatus.blocked
    assert any(c["name"] == "critical_pass_rate" for c in findings["checks"])


def test_threshold_passes_when_rules_met():
    status, _ = evaluate_thresholds(
        pass_rate=0.92,
        rules={"pass_rate": 0.85, "critical_pass_rate": 1.0},
        regressions=[],
        critical_failures=0,
        security_failures=0,
    )
    assert status == ReleaseCheckStatus.passed
