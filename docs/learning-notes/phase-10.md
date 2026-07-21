# Phase 10 — LangGraph Adapter and OpenTelemetry

## What we built

- **RuntimeAdapter** protocol and registry (`app/runtimes/`) dispatching `native` vs `langgraph`.
- **Native adapter** — tool loop via `stream_native_turn`, simple path via `stream_simple_turn`.
- **LangGraph adapter** — prepare `StateGraph` then same streaming helpers (mock-friendly).
- **Version API/UI** — `runtime_type` on `VersionCreate` and agent version form.
- **OpenTelemetry** — `app/observability/otel.py`, FastAPI instrumentation, spans for agent turn, provider, retrieval, tools; console (dev) or OTLP.
- **Docs** — [otel-backends.md](../integrations/otel-backends.md) for Langfuse/Phoenix OTLP.

## Defaults

- `runtime_type` defaults to **native**.
- OTel console exporter in development; disabled in `APP_ENV=test`.
- Product `chat_traces` unchanged.

## Verification

```bash
cd apps/api && pytest tests/integration/test_langgraph_adapter.py -v
```

## Next

Phase 11 — production deployment, observability hardening, portfolio docs.
