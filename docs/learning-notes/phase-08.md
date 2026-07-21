# Phase 8 — Comparison, Regression, MLflow

## What we built

- Alembic `008_phase8`: comparison runs, regression results, release threshold templates, release checks
- `app/comparisons/`: engine, regression rules, service, API (`POST/GET /comparisons`, `GET /regressions`)
- `app/mlflow_tracking/logger.py`: logs eval params/metrics/artifacts when `MLFLOW_TRACKING_URI` set; synthetic id otherwise
- `app/release/`: threshold seed, release-check, mark-release-ready endpoints
- Docker `mlflow` service + env wiring
- Web: `/comparisons`, agent release check / mark ready, dashboard regressions count, nav link

## Design choices

- Comparisons require two **completed** eval runs (reuse runs to save cost)
- No AI comparison summary (Phase 9)
- Release check without `eval_run_id` starts async release eval and returns `blocked` until re-run
- `mark-release-ready` only after latest check `passed`

## Verification

```bash
cd apps/api && pytest tests/unit/test_regression_detection.py -v
cd apps/web && npm run build
```

## Next (Phase 9)

- Improvement tools, red-team, Promptfoo export, Ragas adapter
