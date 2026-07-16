# Phase 4 — Knowledge and RAG

## What we built

- **Schema:** Alembic `004_phase4` — `knowledge_collections`, `documents`, `document_chunks` (pgvector + tsvector), `agent_version_collections`, `background_jobs`
- **Embedding providers:** `MockEmbeddingProvider` (deterministic, default) and `OpenAICompatibleEmbeddingProvider` via `EMBEDDING_*` config
- **Ingestion:** MD/TXT/FAQ CSV/text PDF upload, heading-aware chunking, sync processing in tests / Celery `process_document` in dev
- **Retrieval:** semantic + keyword + RRF hybrid in `RetrievalService`
- **Runtime:** `chat_runtime` injects delimited RAG block and fills `trace.retrieved_chunks`
- **API:** knowledge CRUD, upload, ready-check, reprocess/reindex; retrieval debugger; agent version collection link + RAG toggle
- **UI:** `/knowledge`, collection detail, document inspection, `/retrieval-debugger`, TracePanel citations, playground RAG config

## API endpoints

| Area | Routes |
| --- | --- |
| Collections | `GET/POST /knowledge/collections`, `GET/PATCH/DELETE .../{id}`, `POST .../ready-check` |
| Documents | `POST .../documents` (multipart), `GET /knowledge/documents/{id}`, `.../text`, `.../chunks`, reprocess/reindex/archive |
| Retrieval | `POST /knowledge/retrieval/debug` |
| Agent versions | `GET/PUT /agents/{id}/versions/{vid}/collections`, `PATCH .../rag` |

## Docker

- `worker` service runs Celery against Redis
- Shared `uploads` volume on `api` and `worker`

## Configuration

| Variable | Purpose |
| --- | --- |
| `EMBEDDING_BASE_URL` | OpenAI-compatible embeddings base URL |
| `EMBEDDING_API_KEY` | API key (empty = mock embeddings) |
| `EMBEDDING_MODEL` | Model name (default `text-embedding-3-small`) |
| `EMBEDDING_DIMENSIONS` | Vector size (default 1536) |

## Tests

- `test_chunking.py`, `test_retrieval.py`
- `test_api_knowledge.py` — upload, chunks, RAG trace, debugger
- `knowledge-upload.spec.ts` (E2E with `PLAYWRIGHT_E2E=1`)

## Deferred (later phases)

- `knowledge_search` tool execution (Phase 5)
- OCR / image-only PDF
- Reranking and SSE citation events
- ERP sample-pack document install (Phase 9)

## Verification

```bash
cd apps/api && ruff format --check . && ruff check . && mypy app && pytest tests/ -v
cd apps/web && npm run prepare && npm run lint && npm run typecheck && npm run test && npm run build
```
