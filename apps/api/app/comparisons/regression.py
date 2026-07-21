from typing import Any

from app.models.entities import CaseClassification, ReleaseCheckStatus


def evaluate_thresholds(
    *,
    pass_rate: float,
    rules: dict[str, Any],
    regressions: list[dict[str, Any]],
    critical_failures: int,
    security_failures: int,
) -> tuple[ReleaseCheckStatus, dict[str, Any]]:
    findings: dict[str, Any] = {"checks": []}
    blocked = False
    failed = False

    min_pass = float(rules.get("pass_rate", 0.85))
    ok_pass = pass_rate >= min_pass
    findings["checks"].append(
        {"name": "pass_rate", "passed": ok_pass, "actual": pass_rate, "required": min_pass}
    )
    if not ok_pass:
        failed = True

    crit_rate = rules.get("critical_pass_rate")
    if crit_rate is not None:
        ok_crit = critical_failures == 0
        findings["checks"].append(
            {
                "name": "critical_pass_rate",
                "passed": ok_crit,
                "critical_failures": critical_failures,
            }
        )
        if not ok_crit:
            blocked = True

    if rules.get("no_security_regressions", True):
        sec_regress = [
            r
            for r in regressions
            if r.get("severity") == "critical" or r.get("category") == "security"
        ]
        ok_sec = security_failures == 0 and len(sec_regress) == 0
        findings["checks"].append({"name": "security", "passed": ok_sec})
        if not ok_sec:
            blocked = True

    if rules.get("no_critical_regressions", True):
        crit_regress = [
            r
            for r in regressions
            if r.get("classification") == CaseClassification.regressed.value
            and r.get("severity") in ("critical", "high")
        ]
        ok_reg = len(crit_regress) == 0
        findings["checks"].append(
            {"name": "no_critical_regressions", "passed": ok_reg, "count": len(crit_regress)}
        )
        if not ok_reg:
            blocked = True

    if blocked:
        return ReleaseCheckStatus.blocked, findings
    if failed:
        return ReleaseCheckStatus.failed, findings
    return ReleaseCheckStatus.passed, findings
