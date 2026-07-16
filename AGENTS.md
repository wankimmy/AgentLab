# AgentLab — AI Assistant Rules

Rules for AI coding assistants (Cursor, Codex, Claude Code) working in this repository.

## Phase Gates

1. **Phase 0 (design)** must be approved before any application feature code.
2. Implement **one phase at a time** per [implementation-plan.md](docs/implementation-plan.md).
3. Each phase requires: tests, lint, typecheck, build, security review, learning notes, focused commit.
4. Never claim something works without running verification commands.

## Codex Rules (Mandatory)

1. Never claim a test passed without running it.
2. Never hide failing tests.
3. Never delete tests just to make CI green.
4. Never hide operational errors.
5. Never weaken security for convenience.
6. Never commit credentials.
7. Never expose credentials to the frontend.
8. Never introduce a large dependency without justification.
9. Never invent production metrics.
10. Never store hidden model reasoning.
11. Never permit arbitrary code execution.
12. Never permit arbitrary shell execution.
13. Never permit arbitrary SQL execution.
14. Never permit unrestricted HTTP access.
15. Never treat LLM Judge as objective truth.
16. Never allow judge scores to hide deterministic failures.
17. Never automatically apply AI suggestions.
18. Never run expensive AI operations without explicit user action.
19. Never overwrite historical versions.
20. Never mark a version release ready automatically.
21. Never use confidential real-world data in examples.
22. Prefer small, testable modules.
23. Use typed interfaces.
24. Keep the MVP focused.
25. Explain important architectural decisions.
26. Update documentation when architecture changes.
27. Maintain audit trails.
28. Record limitations honestly.
29. Review AI-generated code.
30. Ensure the implementation can be explained in a technical interview.
31. Ask questions only when genuinely blocking.
32. Make reasonable documented assumptions for non-blocking decisions.
33. Do not implement application features before Phase 0 approval.
34. Complete one implementation phase at a time.
35. Run verification before claiming completion.

## Architecture

- Modular monolith: Nuxt web + FastAPI API + Celery workers.
- PostgreSQL + pgvector is source of truth.
- Native agent runtime (LangGraph optional in Phase 10).
- OpenAI-compatible provider abstraction.
- See [system-design.md](docs/system-design.md) for full architecture.

## Code Conventions

### Python (backend)

- Python 3.12, FastAPI 0.139.x
- Ruff for format + lint; mypy for type checking
- SQLAlchemy 2.x with Alembic migrations
- Async only where practical (streaming, external APIs, concurrent eval)
- Imports at top of file (no inline imports)
- Exhaustive switch with `never` check on union types

### TypeScript (frontend)

- Nuxt 4.4.x, Vue 3 Composition API
- Tailwind CSS + reka-ui components
- Pinia only when shared client state is genuinely required
- Vitest for unit tests; Playwright for E2E

### Module structure (backend)

Each domain module: `models/`, `schemas/`, `repositories/`, `services/`, `router.py`.

### Commits

- One focused commit per phase milestone.
- Only commit when explicitly requested.
- Never commit `.env` or secrets.

## Verification Commands

```bash
# Backend
cd apps/api && ruff format --check . && ruff check . && mypy app && pytest tests/ -v

# Frontend
cd apps/web && npm run lint && npm run typecheck && npm run test && npm run build

# E2E (requires docker compose up)
npx playwright test
```

## Design Documents

Read relevant design doc before implementing a subsystem:

| Subsystem | Document |
| --- | --- |
| Product scope | [product-requirements.md](docs/product-requirements.md) |
| API | [api-design.md](docs/api-design.md) |
| Database | [database-design.md](docs/database-design.md) |
| Providers | [provider-design.md](docs/provider-design.md) |
| Runtime | [agent-runtime-design.md](docs/agent-runtime-design.md) |
| RAG | [rag-design.md](docs/rag-design.md) |
| Tools | [tool-design.md](docs/tool-design.md) |
| Evaluation | [evaluation-design.md](docs/evaluation-design.md) |
| Security | [security-design.md](docs/security-design.md) |
| Deployment | [deployment-design.md](docs/deployment-design.md) |
| Testing | [testing-strategy.md](docs/testing-strategy.md) |

## Learning Notes

After each phase, create `docs/learning-notes/phase-XX.md` covering what was built, design choices, concepts, risks, testing, and interview questions.
