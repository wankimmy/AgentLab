# Phase 1 Learning Notes

## 1. What was built

- Monorepo scaffold with `apps/api` (FastAPI), `apps/web` (Nuxt 4), and `workers/` stub
- Docker Compose dev stack: PostgreSQL + pgvector, Redis, API, web
- Session-based authentication (signed cookie, bcrypt passwords)
- Agent CRUD with immutable version history
- Nine seeded agent templates and three tool definitions
- MockProvider stub for deterministic CI responses
- GitHub Actions CI for backend and frontend

## 2. Why this design

- **Modular monolith:** Single codebase, clear module boundaries, deployable as separate containers without microservice overhead.
- **Immutable versions:** Every config change creates a new `agent_versions` row so comparisons and regression detection have a reliable audit trail.
- **Session cookies over JWT in localStorage:** HttpOnly cookies reduce XSS token theft risk for a browser-first portfolio app.
- **Sync SQLAlchemy for Phase 1:** Streaming and heavy concurrency come in later phases; sync routes are simpler to test and reason about.

## 3. Important Python concepts

- FastAPI dependency injection (`Depends(get_db)`, `CurrentUser`)
- SQLAlchemy 2.0 `Mapped` typed models
- Alembic migrations for schema evolution
- Pydantic v2 request/response schemas with `model_validate`
- `itsdangerous` URL-safe timed serializers for session tokens

## 4. Important AI concepts

- Agent vs agent version separation (configuration snapshot)
- Template library as read-only seed data (applying copies config, does not link live)
- Mock provider pattern for testable LLM integrations without API cost

## 5. Important ML concepts

- Version tracking as foundation for experiment comparison (MLflow in Phase 8)
- Template metadata includes eval starter packs and release thresholds (used later)

## 6. Alternatives considered

| Alternative | Why not chosen for Phase 1 |
| --- | --- |
| JWT in localStorage | Higher XSS exposure; cookies fit single-owner browser app |
| Async SQLAlchemy everywhere | Added complexity without benefit for CRUD-only routes |
| SQLite for dev | pgvector and PostgreSQL ENUMs required from day one |
| LangGraph runtime | Native runtime first per ADR-002 |

## 7. Security risks

- Default `APP_SECRET_KEY` and owner password in `.env.example` must be changed in production
- Rate limiting fails open if Redis is down (documented; acceptable for dev)
- Demo account not yet implemented (Phase 11)

## 8. Production risks

- No HTTPS in local Compose (Traefik in Phase 11)
- Migrations run on container start; production needs backup-before-migrate procedure
- Single owner model; no multi-tenant isolation

## 9. Cost risks

- Phase 1 makes no paid LLM calls (MockProvider only)
- Redis/Postgres resource usage minimal at this stage

## 10. How to test manually

1. `cp .env.example .env`
2. `docker compose up -d --build`
3. Open http://localhost:3000/login
4. Sign in with `owner@agentlab.local` / `changeme`
5. Create agent from ERP Support template
6. Open agent detail, create v2 with new prompt
7. Confirm v1 prompt unchanged in versions list

## 11. Common failure scenarios

| Failure | Cause | Fix |
| --- | --- | --- |
| API not ready | Postgres still starting | Wait for healthcheck, retry |
| Login 401 | Owner not seeded | Run `python -m app.seed` in API container |
| CORS error | Wrong `CORS_ORIGINS` | Match web URL in `.env` |
| Tests fail locally | No Postgres/Redis | Start `docker compose up postgres redis` |

## 12. Interview questions

1. **Why immutable agent versions?** So prompt/model changes are auditable and comparable; never overwrite history.
2. **How does session auth work?** Signed cookie with user ID, verified server-side; bcrypt for passwords.
3. **Why modular monolith?** Portfolio scale does not need microservices; modules allow future extraction.
4. **What is MockProvider for?** Deterministic tests and zero API cost in CI.
5. **How do templates relate to agents?** Templates are versioned library entries; applying one copies config into a new agent version snapshot.

## 13. Suggested interview answers

See sections 2, 3, and 12 above. Emphasize: evaluation-centric product, not a chatbot wrapper; Phase 1 lays identity, versioning, and auth foundations for RAG and eval in later phases.
