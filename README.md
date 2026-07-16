# AgentLab

AgentLab is an AI agent playground and evaluation platform for developers and product teams.

**Status:** Phase 3 complete — playground with streaming chat, traces, and provider abstraction.

## Quick start

```bash
cp .env.example .env
docker compose up -d --build
```

- Web: http://localhost:3000
- API: http://localhost:8000/api/v1/health
- Login: `owner@agentlab.local` / `changeme` (change in `.env`)
- New users are guided through the **onboarding wizard** before reaching the dashboard.
- Playground uses **MockProvider** by default; set `AI_BASE_URL` and `AI_API_KEY` in `.env` for live OpenAI-compatible chat.

## Development

```bash
# API (requires Postgres + Redis)
cd apps/api
pip install -r requirements.txt
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload

# Web
cd apps/web
npm install
npm run dev
```

## Verification

```bash
make test
# or individually:
cd apps/api && pytest tests/ -v
cd apps/web && npm run test && npm run build
```

## Documentation

| Document | Purpose |
| --- | --- |
| [Implementation Plan](docs/implementation-plan.md) | Phased delivery |
| [System Design](docs/system-design.md) | Architecture |
| [AGENTS.md](AGENTS.md) | AI assistant rules |
| [Phase 1 Notes](docs/learning-notes/phase-01.md) | What Phase 1 built |
| [Phase 2 Notes](docs/learning-notes/phase-02.md) | Onboarding, templates, learning centre |
| [Phase 3 Notes](docs/learning-notes/phase-03.md) | Playground, streaming, traces |

## Stack

- Nuxt 4 + Vue 3 + TypeScript + Tailwind
- FastAPI + SQLAlchemy + Alembic
- PostgreSQL 16 + pgvector
- Redis 7

## License

MIT — see [LICENSE](LICENSE).
