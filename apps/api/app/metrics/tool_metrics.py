from app.metrics.types import CaseInput, MetricOutcome, TraceSnapshot
from app.models.entities import MetricType


def _tool_calls(trace: TraceSnapshot) -> list[dict]:
    calls: list[dict] = []
    for req in trace.tool_requests or []:
        if isinstance(req, dict):
            calls.append(req)
    return calls


def _tool_results(trace: TraceSnapshot) -> list[dict]:
    results: list[dict] = []
    for res in trace.tool_results or []:
        if isinstance(res, dict):
            results.append(res)
    return results


def run_tool_metrics(case: CaseInput, trace: TraceSnapshot) -> list[MetricOutcome]:
    results: list[MetricOutcome] = []
    calls = _tool_calls(trace)
    tool_results = _tool_results(trace)

    if case.expected_tool:
        names = [
            c.get("name") or c.get("tool_name") or c.get("function", {}).get("name", "")
            for c in calls
        ]
        passed = case.expected_tool in names
        results.append(
            MetricOutcome(
                metric_name="expected_tool",
                metric_type=MetricType.tool,
                passed=passed,
                details={"expected": case.expected_tool, "called": names},
            )
        )

    if case.expected_tool and case.expected_tool_args:
        matched_call = next(
            (c for c in calls if (c.get("name") or c.get("tool_name")) == case.expected_tool),
            None,
        )
        passed = False
        actual_args: dict = {}
        if matched_call:
            actual_args = matched_call.get("arguments") or matched_call.get("args") or {}
            if isinstance(actual_args, str):
                actual_args = {"raw": actual_args}
            passed = all(
                str(actual_args.get(k)) == str(v) for k, v in case.expected_tool_args.items()
            )
        results.append(
            MetricOutcome(
                metric_name="expected_tool_args",
                metric_type=MetricType.tool,
                passed=passed,
                details={"expected": case.expected_tool_args, "actual": actual_args},
            )
        )

    if calls or case.expected_tool:
        errors = [r for r in tool_results if r.get("error") or r.get("status") == "error"]
        results.append(
            MetricOutcome(
                metric_name="tool_execution_success",
                metric_type=MetricType.tool,
                passed=not errors,
                details={"errors": errors[:3]},
            )
        )

    return results
