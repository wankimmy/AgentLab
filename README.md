# AgentLab

AgentLab is an AI agent playground and evaluation platform for developers and product teams.

**Status:** Phase 1 complete — foundation (auth, agents, versions, templates, CI).

## Quick start

```bash
cp .env.example .env
docker compose up -d --build
```

- Web: http://localhost:3000
- API: http://localhost:8000/api/v1/health
- Login: `owner@agentlab.local` / `changeme` (change in `.env`)

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

## Stack

- Nuxt 4 + Vue 3 + TypeScript + Tailwind
- FastAPI + SQLAlchemy + Alembic
- PostgreSQL 16 + pgvector
- Redis 7

## License

MIT — see [LICENSE](LICENSE).
