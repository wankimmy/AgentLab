# Phase 3 — Playground

## What we built

- **Provider layer:** `ChatProvider` protocol, async `MockProvider` with streaming, `OpenAICompatibleProvider` for live endpoints
- **Model registry:** `model_registry` + `model_pricing` tables with seed data for mock and OpenAI placeholder
- **Conversations API:** CRUD, SSE message streaming, clear, regenerate, summary stub
- **Traces API:** per-turn `chat_traces` + `trace_events` with tokens, cost, latency, TTFT
- **Feedback API:** `POST /messages/{id}/feedback`
- **Playground UI:** three-panel layout (config / chat / trace), Pinia overrides, save-as-version

## Database

Alembic `003_phase3` adds: `conversations`, `messages`, `chat_traces`, `trace_events`, `model_registry`, `model_pricing`, `message_feedback`.

## API endpoints

| Area | Routes |
| --- | --- |
| Conversations | `GET/POST /conversations`, `GET/DELETE /conversations/{id}`, `POST .../messages` (SSE), `POST .../clear`, `POST .../messages/{mid}/regenerate`, `POST .../summary/regenerate` |
| Messages | `POST /messages/{id}/feedback` |
| Traces | `GET /traces`, `GET /traces/{id}` |
| Models | `GET /models` |

## Frontend routes

- `/playground` — agent/version picker
- `/playground/[agentVersionId]` — three-panel playground with mobile tabs

## Memory modes

- `none` — system + current user only
- `conversation` — full history
- `summarised` — summary stub + last 20 messages

## Tests

- `test_streaming.py`, `test_api_conversations.py`
- `test_mock_provider.py` (async stream)
- `sseParser.test.ts`
- `playground.spec.ts` (E2E with `PLAYWRIGHT_E2E=1`)

## Configuration

Set `AI_BASE_URL` and `AI_API_KEY` in `.env` for live OpenAI-compatible providers. Default is MockProvider (`provider: mock` on agent versions).

## Deferred (later phases)

- Tool execution loop (Phase 5)
- RAG retrieval in chat (Phase 4)
- LLM judge on messages (Phase 6)

## Verification

```bash
cd apps/api && ruff format --check . && ruff check . && mypy app && pytest tests/ -v
cd apps/web && npm run prepare && npm run lint && npm run typecheck && npm run test && npm run build
```
