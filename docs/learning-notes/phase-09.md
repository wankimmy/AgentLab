# Phase 9 — Improvement Tools

## What we built

- **Schema:** `prompt_recommendations`, `red_team_runs` / `red_team_cases`, `comparison_runs.ai_summary` + status (migration `009_phase9`).
- **Celery tasks:** `generate_eval_cases`, `analyse_prompt`, `run_red_team`, `summarize_comparison` (eager in test).
- **Draft test generation:** `POST /evaluations/datasets/{id}/generate` with cost estimate; cases stay `draft`.
- **Prompt workspace:** structural checks + recommendations; accept/dismiss only (no auto-apply).
- **Comparison summary:** `POST /comparisons/{id}/summary` (manual, confirm).
- **Red team:** `/red-team` APIs + UI; audit `red_team.start`; promote to draft eval case.
- **Exports:** `POST /exports/promptfoo` (YAML/JSON).
- **Ragas adapter:** `context_precision` / `context_recall` with heuristic fallback when `ragas` is not installed.
- **ERP sample pack:** install creates agent, 7 synthetic knowledge docs, dataset with 25 cases.

## Defaults

- Expensive AI operations require `confirm: true` after estimate.
- Generated cases and prompt suggestions remain drafts until the user approves or applies manually.
- Red-team payloads are synthetic only.

## Verification

```bash
cd apps/api && pytest tests/unit/test_ragas_adapter.py tests/integration/test_red_team.py -v
```

## Next

Phase 10 — LangGraph adapter and OpenTelemetry exporters.
