# AgentLab Implementation Plan

Phased delivery plan for AgentLab. Each phase produces working, testable software. Complete phases in order. Do not skip ahead.

**Prerequisite:** Phase 0 design package approved.

## Stack Versions

| Component | Version |
| --- | --- |
| Nuxt | 4.4.x |
| Python | 3.12 |
| FastAPI | 0.139.x |
| PostgreSQL | 16 + pgvector 0.8.x |
| Redis | 7.x |
| Celery | 5.x |

---

## Phase 1 — Foundation

**Goal:** Monorepo scaffold, dev environment, auth, agent CRUD, versioning, CI.

### Deliverables

- [x] Monorepo structure (`apps/web`, `apps/api`, `workers`, `infrastructure`, `tests`)
- [x] `docker-compose.yml` (postgres, redis, api, web)
- [x] FastAPI app with health/ready endpoints
- [x] Nuxt app with login page and app shell
- [x] PostgreSQL + Alembic initial migration (users, agents, agent_versions, tools, agent_templates)
- [x] Session auth (login, logout, me, bcrypt, rate limit)
- [x] Agent CRUD + immutable version creation
- [x] Template data model + seed 9 templates (config only)
- [x] `.env.example`, Makefile, GitHub Actions CI (lint, test, build)
- [x] Mock provider stub

### Acceptance criteria

- Owner can log in and see empty dashboard
- Owner can create agent with initial draft version
- Creating new version does not mutate previous version
- CI passes: ruff, mypy, pytest, eslint, vitest, nuxt build
- `docker compose up` starts all dev services

### Verification

```bash
docker compose up -d
cd apps/api && pytest tests/ -v
cd apps/web && npm run build
curl http://localhost:8000/api/v1/health
```

### Commit

`feat(phase-1): foundation — monorepo, auth, agents, versions, CI`

---

## Phase 2 — Onboarding and Templates

**Goal:** Setup wizard, template library UI, inline guidance, empty states, learning centre foundation.

### Deliverables

- [x] Onboarding wizard (8 steps, saved progress)
- [x] Template browse/preview/apply UI
- [x] Template seed data with full config (prompts, eval packs, rubrics)
- [x] Inline help panels on major pages
- [x] Guided empty states (no agents, knowledge, datasets, evals)
- [x] Learning centre with foundation guides (seed content)
- [x] Sample pack data model + ERP pack stub

### Acceptance criteria

- New user completes onboarding wizard end-to-end
- Applying ERP Support template creates agent with prompt and tools configured
- Help panels render on agent, playground (stub), and knowledge pages
- Learning centre shows at least 5 foundation articles

### Verification

```bash
cd apps/api && pytest tests/integration/test_onboarding.py -v
npx playwright test tests/e2e/onboarding.spec.ts
```

### Commit

`feat(phase-2): onboarding, templates, guidance, learning centre`

---

## Phase 3 — Playground

**Goal:** Provider abstraction, streaming chat, conversations, traces, cost estimates.

### Deliverables

- [x] OpenAI-compatible provider adapter + MockProvider
- [x] Model capability registry + pricing table
- [x] Conversation CRUD + message persistence
- [x] SSE streaming endpoint for chat
- [x] Three-panel playground UI (config, chat, trace)
- [x] Temporary overrides with visual indicator
- [x] Trace recording (tokens, cost, latency, TTFT)
- [x] Human feedback (rating + notes)
- [x] Memory modes (none, conversation, summarised)

### Acceptance criteria

- User sends message in playground and receives streamed response
- Trace panel shows tokens, cost, duration
- Overrides clearly marked; save-as-version creates new draft
- MockProvider used in CI tests

### Verification

```bash
cd apps/api && pytest tests/integration/test_streaming.py -v
npx playwright test tests/e2e/playground.spec.ts
```

### Commit

`feat(phase-3): playground, streaming, traces, provider abstraction`

---

## Phase 4 — Knowledge and RAG

**Goal:** Collections, upload, processing, chunking, embeddings, retrieval, citations, debugger.

### Deliverables

- [ ] Knowledge collections CRUD + readiness checks
- [ ] Document upload with validation
- [ ] Celery tasks: extract, chunk, embed, store
- [ ] pgvector search + keyword search + hybrid
- [ ] Retrieval service integrated into runtime
- [ ] Citation generation
- [ ] Retrieval debugger UI
- [ ] Knowledge guides (in-app content)
- [ ] Document inspection UI (text, chunks, metadata)
- [ ] Re-index manual actions with cost warning

### Acceptance criteria

- Upload PDF/MD/TXT/FAQ CSV → document processes → chunks visible
- Playground with RAG enabled shows retrieved chunks in trace
- Retrieval debugger returns scored chunks for test query
- Collection readiness check validates checklist

### Verification

```bash
cd apps/api && pytest tests/integration/test_api_knowledge.py tests/unit/test_retrieval.py -v
npx playwright test tests/e2e/knowledge-upload.spec.ts
```

### Commit

`feat(phase-4): knowledge, RAG, retrieval, citations, debugger`

---

## Phase 5 — Tools and Runtime

**Goal:** Native agent runtime with calculator, knowledge search, current time, approval, limits.

### Deliverables

- [ ] Native runtime loop (steps, tools, streaming, limits)
- [ ] Calculator tool (safe parser, no eval)
- [ ] Knowledge search tool
- [ ] Current datetime tool
- [ ] Tool approval flow (SSE + approve/reject API)
- [ ] Audit logging for tool executions
- [ ] RAG safety delimiters in context assembly
- [ ] Guardrails (input/output limits, allowlist)

### Acceptance criteria

- Agent calls calculator in playground and returns correct result
- Approval-required tool pauses and waits for user decision
- Step/call limits enforced; error shown when exceeded
- Red-team-relevant: document instructions do not override system prompt

### Verification

```bash
cd apps/api && pytest tests/unit/test_calculator_tool.py tests/integration/test_tool_approval.py -v
```

### Commit

`feat(phase-5): native runtime, tools, approval, audit`

---

## Phase 6 — Evaluation Foundations

**Goal:** Datasets, cases, deterministic/semantic/RAG metrics, background eval.

### Deliverables

- [ ] Evaluation dataset + version CRUD
- [ ] Test case CRUD + CSV/JSON import/export
- [ ] Evaluation templates (8 presets)
- [ ] Deterministic metrics engine (all metrics from eval design)
- [ ] Semantic similarity metric
- [ ] RAG metrics (retrieval, citation)
- [ ] Tool metrics
- [ ] Quick Check and Standard modes
- [ ] Celery evaluation worker
- [ ] Eval run UI (estimate → confirm → progress → results)
- [ ] Failure explanations

### Acceptance criteria

- Create dataset with 10 cases, run Quick Check, see pass/fail per case
- Deterministic failure shown even if judge would pass
- Eval run executes in background with progress updates
- Failed cases show explanation with expected vs actual

### Verification

```bash
cd apps/api && pytest tests/unit/test_deterministic_metrics.py tests/integration/test_api_evaluations.py -v
npx playwright test tests/e2e/evaluation-run.spec.ts
```

### Commit

`feat(phase-6): evaluation datasets, metrics, background eval`

---

## Phase 7 — LLM Judge and Human Review

**Goal:** Judge provider, rubrics, structured output, multi-judge, human review.

### Deliverables

- [ ] Judge provider adapter (separate model)
- [ ] Rubric templates (6 criteria)
- [ ] Structured judge output with schema validation
- [ ] Manual playground judge action
- [ ] Standard eval judge integration
- [ ] Release eval judge (required)
- [ ] Multi-judge review
- [ ] Human review recording
- [ ] Blind A/B comparison UI
- [ ] Judge limitations notice in UI

### Acceptance criteria

- Manual "Run LLM Judge" on playground response returns scored rubric
- Standard eval with judge enabled produces judge scores per case
- Multi-judge shows individual scores and agreement
- Human review recorded and visible on result

### Verification

```bash
cd apps/api && pytest tests/unit/test_judge_schema.py tests/integration/test_judge.py -v
```

### Commit

`feat(phase-7): LLM judge, rubrics, multi-judge, human review`

---

## Phase 8 — Comparison, Regression, MLflow

**Goal:** Version comparison, regression detection, release thresholds, MLflow integration.

### Deliverables

- [ ] Version/model/settings comparison runs
- [ ] Regression detection engine + rules
- [ ] Comparison UI (deltas, improved/regressed/unchanged)
- [ ] Release threshold templates
- [ ] MLflow logging (params, metrics, artifacts)
- [ ] Release evaluation mode
- [ ] Release check flow
- [ ] Mark release ready (manual, after check pass)

### Acceptance criteria

- Compare two versions shows pass-rate delta and case-level changes
- Regression detected when previously passing case fails
- MLflow run created for each evaluation with correct parameters
- Release check blocks when critical failure exists

### Verification

```bash
cd apps/api && pytest tests/unit/test_regression_detection.py -v
npx playwright test tests/e2e/comparison.spec.ts tests/e2e/release-check.spec.ts
```

### Commit

`feat(phase-8): comparison, regression, MLflow, release check`

---

## Phase 9 — Improvement Tools

**Goal:** AI test generation, prompt analysis, red-team, Promptfoo export, Ragas adapter.

### Deliverables

- [ ] AI test case generation (manual, draft cases)
- [ ] Prompt analysis and improvement suggestions
- [ ] Improvement workspace (failed cases → suggestions)
- [ ] Comparison AI summary (manual)
- [ ] Red-team testing (manual, categorized attacks)
- [ ] Promptfoo export
- [ ] Ragas adapter (selected metrics)
- [ ] ERP Support sample pack (full install)

### Acceptance criteria

- Generate 5 draft test cases from agent config
- Red-team run executes injection cases and reports pass/fail
- Promptfoo export produces valid config file
- ERP sample pack installs agent + knowledge + 25 eval cases

### Verification

```bash
cd apps/api && pytest tests/unit/test_ragas_adapter.py tests/integration/test_red_team.py -v
```

### Commit

`feat(phase-9): improvement tools, red-team, exports, sample pack`

---

## Phase 10 — Optional Runtime and Integrations

**Goal:** LangGraph adapter, OpenTelemetry exporters.

### Deliverables

- [ ] Runtime adapter interface formalised
- [ ] LangGraph runtime adapter (optional per agent version)
- [ ] OpenTelemetry SDK integration
- [ ] OTLP exporter configuration
- [ ] Documented adapter points for Langfuse/Phoenix

### Acceptance criteria

- Agent version can select `langgraph` runtime
- OTel spans visible in console exporter during dev
- Native runtime remains default and fully functional

### Verification

```bash
cd apps/api && pytest tests/integration/test_langgraph_adapter.py -v
```

### Commit

`feat(phase-10): LangGraph adapter, OpenTelemetry`

---

## Phase 11 — Production Readiness

**Goal:** Observability, security hardening, CI/CD deploy, backup, portfolio docs.

### Deliverables

- [ ] Prometheus metrics endpoint
- [ ] Structured logging with correlation IDs
- [ ] `docker-compose.production.yml`
- [ ] Traefik HTTPS configuration
- [ ] GitHub Actions deploy workflow
- [ ] Backup and restore scripts (tested)
- [ ] Rollback procedure (tested)
- [ ] Demo read-only account
- [ ] Portfolio documentation (case study, interview prep, runbook, troubleshooting)
- [ ] Security review checklist completed
- [ ] Performance smoke tests

### Acceptance criteria

- HTTPS production deployment works on Hostinger VPS
- Backup and restore tested successfully
- Rollback to previous image tag works
- All CI checks pass
- Portfolio case study complete (no invented metrics)
- Definition of Done (section 66) verified

### Verification

```bash
# Full CI
make test
# Deploy smoke
curl https://agentlab.example.com/api/v1/health
curl https://agentlab.example.com/api/v1/ready
```

### Commit

`feat(phase-11): production deployment, observability, portfolio docs`

---

## Per-Phase Checklist

Every phase must complete:

1. [ ] Update or create tests
2. [ ] Implement feature
3. [ ] Run formatting (ruff format, prettier)
4. [ ] Run linting (ruff check, eslint)
5. [ ] Run static type checking (mypy, nuxt typecheck)
6. [ ] Run unit tests
7. [ ] Run integration tests
8. [ ] Run production builds
9. [ ] Review security implications
10. [ ] Review cost implications
11. [ ] Update documentation
12. [ ] Create `docs/learning-notes/phase-XX.md`
13. [ ] Create focused git commit
14. [ ] Present completed work and known limitations

## Risk Register

| Risk | Phase | Mitigation |
| --- | --- | --- |
| Scope creep | All | Strict phase gates; out-of-scope list |
| Provider API costs | 3+ | MockProvider in CI; cost limits |
| VPS resource limits | 11 | Compose resource limits; MLflow internal |
| RAG injection | 4–5 | Delimiter blocks; red-team in Phase 9 |
| Flaky judge scores | 7 | Deterministic metrics override; multi-judge |

## Post-MVP (Documented Only)

- CrewAI multi-agent adapter
- Arbitrary HTTP/SQL tools
- Public registration and teams
- Kubernetes deployment
- Voice and image agents
