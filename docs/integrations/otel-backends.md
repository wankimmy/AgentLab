# OTLP backend adapters (Langfuse, Phoenix)

AgentLab exports operational traces via **OpenTelemetry OTLP HTTP**. No Langfuse or Phoenix SDK is bundled; point `OTEL_EXPORTER_OTLP_ENDPOINT` at your collector or vendor ingress.

## Environment

```env
OTEL_ENABLED=true
OTEL_SERVICE_NAME=agentlab-api
OTEL_EXPORTER_OTLP_ENDPOINT=https://your-collector/v1/traces
```

When `OTEL_EXPORTER_OTLP_ENDPOINT` is empty, development uses the **console** span exporter (disabled in `APP_ENV=test`).

## Langfuse

1. Create a Langfuse project and copy the OTLP traces endpoint (Cloud: project settings → OpenTelemetry).
2. Set `OTEL_EXPORTER_OTLP_ENDPOINT` to that URL and add required headers per Langfuse docs (often via `OTEL_EXPORTER_OTLP_HEADERS` if your deployment supports it).
3. Spans such as `agent.turn`, `provider.chat`, `retrieval.search`, and `tool.execute` appear in Langfuse trace UI.

## Arize Phoenix

1. Run Phoenix locally or use Arize Cloud OTLP ingress.
2. Set `OTEL_EXPORTER_OTLP_ENDPOINT` to Phoenix OTLP URL (default local collector is often `http://localhost:6006/v1/traces`).
3. Correlate with evaluation runs separately via MLflow (`MLFLOW_TRACKING_URI`).

## Product traces vs OTel

Playground **ChatTrace** rows remain the user-facing trace panel. OTel is for ops/SRE and optional LLM observability backends.
