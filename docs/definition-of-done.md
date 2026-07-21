# Definition of Done — AgentLab MVP

This checklist replaces external master prompt section 66. Verify before calling the product portfolio-complete.

## Platform

- [x] Owner authentication with session cookies and rate-limited login
- [x] Optional demo read-only account (seed + middleware)
- [x] Agents, versions, templates, playground, traces
- [x] Knowledge collections, RAG, retrieval debugger
- [x] Tools, approvals, native runtime
- [x] Evaluation datasets, runs, metrics, judge, human review
- [x] Comparisons, regression, release check, MLflow logging
- [x] Improvement tools (generate drafts, prompt analyse, red-team, exports)
- [x] Native + LangGraph runtime adapters; OpenTelemetry hooks

## Production readiness (Phase 11)

- [x] Prometheus `/metrics` and structured request logging
- [x] `docker-compose.production.yml` + Traefik HTTPS pattern
- [x] Deploy workflow (GHCR + SSH) and ops scripts (backup, restore, rollback, smoke)
- [x] Portfolio and runbook documentation (no invented metrics)
- [x] Security review checklist artifact completed

## Verification commands

```bash
make test
cd apps/api && pytest tests/unit/test_observability.py tests/performance/test_smoke_latency.py -v
infrastructure/scripts/smoke.sh http://localhost:8000
```

Live VPS HTTPS and backup restore drills are documented in [production-runbook.md](production-runbook.md) and executed during deploy.
