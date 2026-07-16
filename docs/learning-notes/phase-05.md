# Phase 5 — Tools and Runtime

## What we built

- **Native runtime loop** in `native_runtime.py`: multi-step LLM + tool execution with limits
- **Tools:** `calculator` (safe AST parser), `knowledge_search` (RetrievalService), `current_datetime`
- **Modes:** `auto`, `approval`, `disabled` via `AgentVersion.tool_config`
- **SSE events:** `tool_call`, `tool_result`, `approval_required`
- **API:** `GET /tools`, `POST /tool-approvals/{id}/approve|reject`, `PATCH .../versions/{id}/tools`
- **Schema:** Alembic `005_phase5` — `tool_approvals`, `audit_logs`
- **MockProvider:** deterministic tool_calls for CI patterns (`calculate:`, math, `what time`, `search:`)
- **UI:** playground approval banner, TracePanel tool sections, tool mode config panel

## Defaults

Runtime limits in `tool_config.limits` (optional):

| Key | Default |
| --- | --- |
| max_agent_steps | 5 |
| max_tool_calls | 3 |
| timeout_seconds | 60 |

## Tests

- `test_calculator_tool.py` — safe math, reject unsafe expressions
- `test_tool_approval.py` — auto calculator + approval flow with audit log

## Deferred

- LangGraph adapter (Phase 10)
- SSE `citation` events (trace JSON sufficient)
- Dynamic tool registration

## Verification

```bash
cd apps/api && ruff format --check . && ruff check . && mypy app && pytest tests/unit/test_calculator_tool.py tests/integration/test_tool_approval.py -v
cd apps/web && npm run prepare && npm run lint && npm run typecheck && npm run test && npm run build
```
