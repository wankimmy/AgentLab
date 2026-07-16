# Phase 6 — Evaluation Foundations

## What we built

- Alembic `006_phase6`: evaluation datasets, versions, cases, runs, results, metric_results
- Metrics package: deterministic (18 checks), semantic cosine, heuristic RAG, tool metrics, engine aggregation
- Eight static evaluation presets via `GET /evaluations/templates`
- Full evaluations API: datasets, versions, cases, import/export, estimate, runs, cancel
- Celery `run_evaluation` task with eager mode in tests
- `run_eval_turn` sync helper wrapping `stream_chat_turn`
- Web UI: runs list, datasets, dataset detail, run wizard (estimate → confirm), run progress/results

## Design choices

- **Datasets owned by `user_id`** — matches other Phase resources even though DB design doc omits it
- **Quick vs Standard** — same engines; Quick uses preset `quick_metrics` subset; judge always off in Phase 6
- **RAG metrics** — heuristic only (no Ragas); retrieval/citation checks from `ChatTrace.retrieved_chunks`
- **Overall pass** — deterministic/tool/RAG failures always fail; semantic alone cannot pass a case
- **Progress** — stored in `config_snapshot.progress` and `BackgroundJob.payload`

## Pitfalls

- Celery worker uses `SessionLocal()` — integration tests rely on `task_always_eager` and router `commit()`
- Mock provider responses won't match `required_keywords` unless cases are tailored — tests use `mock` keyword in even cases
- `from-template` requires seeded `eval_starter_pack` on template version

## Verification

```bash
cd apps/api && pytest tests/unit/test_deterministic_metrics.py tests/integration/test_api_evaluations.py -v
cd apps/web && npm run lint && npm run typecheck && npm run build
PLAYWRIGHT_E2E=1 npx playwright test tests/e2e/evaluation-run.spec.ts
```

## Next (Phase 7)

- LLM judge, rubrics, human review APIs
- Wire `judge_enabled` for Standard mode default
