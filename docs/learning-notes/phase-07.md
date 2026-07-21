# Phase 7 — LLM Judge and Human Review

## What we built

- Alembic `007_phase7`: judge rubric templates, judge runs/results, human reviews, blind A/B reviews
- `JUDGE_*` settings and `get_judge_provider()` (mock JSON judge for CI)
- `app/judges/`: rubrics, schema validation, prompts, service, multi-judge agreement, API router
- `POST /messages/{id}/judge`, `GET /judges/rubrics`, `POST /judges/multi-review`
- `POST /evaluations/results/{id}/review`, `POST /reviews/blind-ab`
- Eval runs: Standard/Release default judge on; runner persists `llm_judge` metric; cap 100 judge calls/run
- Web: playground judge button, eval wizard (Release + judge toggle), run results human review + multi-judge, blind A/B page

## Design choices

- Deterministic/tool/RAG failures are never overridden by judge pass
- Mock judge when `JUDGE_API_KEY` unset (same pattern as chat mock)
- Judge cost folded into estimate via multiplier + per-case mock cost
- `HumanReviewVerdict.pass_` maps to API value `pass`

## Pitfalls

- Integration tests need Postgres (docker compose `postgres` service)
- `asyncio.run` inside Celery eval worker for judge calls — acceptable for MVP sync judge
- Blind A/B UI uses message IDs; preview text is display-only until submit reveals labels

## Verification

```bash
cd apps/api && ruff format --check . && ruff check . && mypy app && pytest tests/unit/test_judge_schema.py tests/integration/test_judge.py -v
cd apps/web && npm run lint && npm run typecheck && npm run build
```

## Next (Phase 8)

- Version comparison, regression detection, MLflow, release check flow
