# Phase 2 — Onboarding and Templates

## What we built

- **Onboarding wizard** (`/onboarding`): 8-step flow with saved progress via `PUT /onboarding/progress`, rule-based `define-draft`, and `POST /onboarding/complete` to create the agent.
- **Templates**: browse (`/templates`), preview (`/templates/[id]`), apply via `POST /templates/{id}/apply`.
- **Learning centre**: 6 seeded foundation guides at `/learning` and `/learning/[slug]`.
- **Sample packs**: ERP synthetic pack with `POST /sample-packs/{id}/install`.
- **Guidance UI**: `HelpPanel`, `EmptyState`, stub pages for knowledge, playground, evaluations.
- **Dashboard**: real agent counts and `onboarding_complete` flag.

## Database

Alembic `002_phase2` adds:

- `onboarding_progress`
- `guides` + `guide_sections`
- `sample_data_packs`

Seed enrichment in `app/seed_data.py` — full ERP template content; lighter packs for other templates.

## API endpoints

| Area | Routes |
| --- | --- |
| Onboarding | `GET/PUT /onboarding/progress`, `POST /onboarding/define-draft`, `POST /onboarding/complete` |
| Guides | `GET /guides`, `GET /guides/{slug}` |
| Sample packs | `GET /sample-packs`, `POST /sample-packs/{id}/install` |
| Templates | `POST /templates/{id}/apply` |
| Dashboard | `GET /dashboard` (counts + onboarding flag) |

## Frontend routes

`/onboarding`, `/templates`, `/templates/[id]`, `/learning`, `/learning/[slug]`, `/sample-packs`, `/knowledge`, `/playground`, `/evaluations`

Login redirects to onboarding when incomplete. `onboarding` middleware guards main app routes.

## Tests

- API integration: `test_onboarding.py`, `test_templates_apply.py`, `test_guides.py`, `test_sample_packs.py`
- Vitest: `HelpPanel.test.ts`, `promptCompleteness.test.ts`
- Playwright: `tests/e2e/onboarding.spec.ts` (run with `PLAYWRIGHT_E2E=1` and stack up)

## Deferred (later phases)

- Real playground streaming (Phase 3)
- Document upload / RAG (Phase 4)
- Quick Check evaluation engine (Phase 6)
- Paid LLM “Help Me Define” (uses deterministic draft only)

## Verification

```bash
cd apps/api && ruff format --check . && ruff check . && mypy app && pytest tests/ -v
cd apps/web && npm run prepare && npm run lint && npm run typecheck && npm run test && npm run build
# E2E (optional, stack running):
# cd apps/web && PLAYWRIGHT_E2E=1 npx playwright test tests/e2e/onboarding.spec.ts
```
