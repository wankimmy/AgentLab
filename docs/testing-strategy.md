# Testing Strategy — AgentLab

## 1. Principles

- Never claim a test passed without running it.
- Never hide failing tests or delete tests to make CI green.
- Mock external model APIs in normal CI (no paid API calls).
- Opt-in live-provider test suite for manual/staging verification.
- Every phase adds tests before or with implementation.
- Deterministic tests are preferred over flaky integration tests.

## 2. Test Pyramid

```text
         ┌─────────┐
         │  E2E    │  Playwright (critical paths)
         ├─────────┤
         │ Integr. │  API + DB + Redis (mock provider)
         ├─────────┤
         │  Unit   │  Services, metrics, parsers, validators
         └─────────┘
```

## 3. Backend Testing (Pytest)

### 3.1 Test structure

```text
tests/
├── unit/
│   ├── test_auth.py
│   ├── test_agents.py
│   ├── test_versions.py
│   ├── test_prompt_diff.py
│   ├── test_provider_mock.py
│   ├── test_calculator_tool.py
│   ├── test_chunking.py
│   ├── test_retrieval.py
│   ├── test_deterministic_metrics.py
│   ├── test_semantic_metrics.py
│   ├── test_judge_schema.py
│   ├── test_cost_calculation.py
│   ├── test_regression_detection.py
│   └── test_security_controls.py
├── integration/
│   ├── test_api_agents.py
│   ├── test_api_conversations.py
│   ├── test_api_knowledge.py
│   ├── test_api_evaluations.py
│   ├── test_streaming.py
│   ├── test_tool_approval.py
│   ├── test_background_jobs.py
│   └── test_rate_limits.py
├── live/
│   └── test_live_provider.py  # opt-in only
└── conftest.py
```

### 3.2 Coverage targets

| Area | Target |
| --- | --- |
| Authentication | 100% |
| Deterministic metrics | 100% |
| Tool execution | 100% |
| Provider adapters | 90% |
| API routes | 80% |
| Overall | 80% |

### 3.3 Mock Provider

`MockProvider` implementation for CI:

| Scenario | Config |
| --- | --- |
| Simple response | Default |
| Tool call response | `scenario=tool_call` |
| Streaming chunks | `scenario=stream` |
| Structured output | `scenario=structured` |
| Timeout | `scenario=timeout` |
| Rate limit | `scenario=rate_limit` |
| Invalid JSON | `scenario=invalid_json` |
| Context overflow | `scenario=context_overflow` |

Deterministic responses based on input hash for reproducible tests.

### 3.4 Key test cases by module

| Module | Tests |
| --- | --- |
| Auth | Login, logout, session expiry, brute force limit, demo read-only |
| Agents | CRUD, versioning immutability, clone, archive |
| Prompts | Diff, completeness score, draft-only edit |
| Streaming | SSE event sequence, cancellation, partial persist |
| Tools | Calculator safety, approval flow, limit enforcement, audit |
| Knowledge | Upload validation, extraction, chunking, embedding storage |
| Retrieval | Vector search, keyword search, hybrid, threshold, citations |
| Evaluation | Deterministic metrics, semantic similarity, RAG metrics |
| Judge | Schema validation, score aggregation, multi-judge |
| Regression | New failure detection, severity classification |
| Security | Rate limits, path traversal, XSS sanitisation |
| Jobs | Enqueue, progress, cancel, retry, idempotency |
| Cost | Token-based calculation, limit enforcement |

## 4. Frontend Testing

### 4.1 Vitest (unit/component)

```text
apps/web/tests/
├── unit/
│   ├── prompt-editor.test.ts
│   ├── cost-estimate.test.ts
│   ├── trace-viewer.test.ts
│   └── completeness-score.test.ts
└── components/
    ├── HelpPanel.test.ts
    ├── TemplateCard.test.ts
    └── EvalResultCard.test.ts
```

### 4.2 Playwright (E2E)

```text
tests/e2e/
├── auth.spec.ts
├── onboarding.spec.ts
├── agent-creation.spec.ts
├── playground.spec.ts
├── knowledge-upload.spec.ts
├── evaluation-run.spec.ts
├── comparison.spec.ts
└── release-check.spec.ts
```

### 4.3 E2E critical paths

| Path | Verification |
| --- | --- |
| Login → Dashboard | Auth cookie, metrics visible |
| Create agent from template | Agent + version created |
| Playground chat | SSE streaming, trace panel |
| Upload document | Processing status, chunk inspection |
| Run Quick Check | Progress, results, failure explanation |
| Manual LLM Judge | Cost modal, judge results |
| Compare versions | Side-by-side results |
| Release check | Pass/fail criteria displayed |

E2E runs against docker-compose dev stack with MockProvider.

## 5. CI Pipeline

### 5.1 Pull request checks

```yaml
jobs:
  backend-lint:
    - ruff format --check
    - ruff check
    - mypy apps/api

  backend-test:
    - pytest tests/ --cov --cov-fail-under=80
    - excludes tests/live/

  frontend-lint:
    - eslint
    - nuxt typecheck

  frontend-test:
    - vitest run

  frontend-build:
    - nuxt build

  migration-check:
    - alembic check
    - alembic upgrade head (test DB)

  security:
    - gitleaks detect
    - pip-audit / npm audit

  container-build:
    - docker build (no push)
```

### 5.2 Production deploy checks

All PR checks plus:

- Push versioned images to GHCR
- Deploy to VPS
- Readiness checks
- Smoke tests (health, login, create agent)

## 6. Live Provider Tests

```bash
LIVE_PROVIDER_TESTS=1 pytest tests/live/ -v
```

Requires valid `AI_*`, `EMBEDDING_*`, `JUDGE_*` env vars. Not run in CI. Documented for manual pre-release verification.

## 7. Test Data

| Source | Purpose |
| --- | --- |
| `tests/fixtures/` | Static test files (PDF, CSV, JSON) |
| `tests/factories/` | Factory functions for DB entities |
| `seed/` | Demo data for manual testing |
| `sample-packs/` | Synthetic ERP pack for E2E |

No confidential data in any test fixture.

## 8. Performance Testing (Phase 11)

| Test | Target |
| --- | --- |
| Chat response P95 | < 5s (with mock provider) |
| Retrieval query | < 500ms |
| Eval run (25 cases) | < 5 min (mock provider) |
| Document processing (10 pages) | < 30s |

## 9. Security Testing

| Test | Tool |
| --- | --- |
| Secret scanning | gitleaks in CI |
| Dependency vulnerabilities | pip-audit, npm audit |
| Red-team cases | Manual suite in app (Phase 9) |
| OWASP ZAP (optional) | Phase 11 security review |

## 10. Verification Per Phase

Each implementation phase must:

1. Add/update tests for new functionality
2. Run formatting and linting
3. Run unit tests
4. Run integration tests (if applicable)
5. Run production build
6. Document known limitations
7. Create learning notes (`docs/learning-notes/phase-XX.md`)

## 11. Test Commands (reference)

```bash
# Backend
cd apps/api && pytest tests/ -v --cov=app
cd apps/api && ruff format --check . && ruff check . && mypy app

# Frontend
cd apps/web && npm run test
cd apps/web && npm run build

# E2E
docker compose up -d
npx playwright test

# All (CI equivalent)
make test  # defined in Phase 1 Makefile
```
