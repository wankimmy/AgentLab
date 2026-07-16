# API Design — AgentLab

## 1. Conventions

- **Base URL:** `/api/v1`
- **Format:** JSON request/response; SSE for streaming endpoints
- **Auth:** Session cookie (`HttpOnly`, `Secure`, `SameSite=Lax`)
- **Errors:** RFC 7807 Problem Details (`application/problem+json`)
- **IDs:** UUID strings
- **Pagination:** `?page=1&page_size=20` with `{ items, total, page, page_size }`
- **Timestamps:** ISO 8601 UTC
- **Idempotency:** `Idempotency-Key` header on expensive POST operations

## 2. Authentication

| Method | Path | Description |
| --- | --- | --- |
| POST | `/auth/login` | Email + password → session cookie |
| POST | `/auth/logout` | Invalidate session |
| GET | `/auth/me` | Current user profile |

## 3. Agents and Versions

| Method | Path | Description |
| --- | --- | --- |
| GET | `/agents` | List agents (filter: status, tag) |
| POST | `/agents` | Create agent (+ initial draft version) |
| GET | `/agents/{id}` | Agent detail with active version |
| PATCH | `/agents/{id}` | Update metadata (not config) |
| POST | `/agents/{id}/archive` | Archive agent |
| POST | `/agents/{id}/restore` | Restore agent |
| POST | `/agents/{id}/clone` | Clone agent |
| GET | `/agents/{id}/versions` | List versions |
| POST | `/agents/{id}/versions` | Create new draft version |
| GET | `/agents/{id}/versions/{vid}` | Version detail |
| POST | `/agents/{id}/versions/{vid}/activate` | Set active version |
| POST | `/agents/{id}/versions/{vid}/duplicate` | Duplicate to new draft |
| GET | `/agents/{id}/versions/compare` | Compare two versions (`?a=&b=`) |
| GET | `/agents/{id}/export` | Export config (no secrets) |
| POST | `/agents/import` | Import config |

## 4. Prompts

| Method | Path | Description |
| --- | --- | --- |
| GET | `/agents/{id}/versions/{vid}/prompt` | Get prompt + completeness score |
| PUT | `/agents/{id}/versions/{vid}/prompt` | Update prompt (draft only) |
| GET | `/agents/{id}/versions/{vid}/prompt/diff` | Diff against parent (`?against=`) |
| POST | `/agents/{id}/versions/{vid}/prompt/analyse` | Manual AI improvement (→ job) |

## 5. Conversations and Playground

| Method | Path | Description |
| --- | --- | --- |
| GET | `/conversations` | List (filter: agent_id) |
| POST | `/conversations` | Create conversation |
| GET | `/conversations/{id}` | Conversation with messages |
| DELETE | `/conversations/{id}` | Delete conversation |
| POST | `/conversations/{id}/messages` | Send message (returns SSE stream) |
| POST | `/conversations/{id}/messages/{mid}/retry` | Retry assistant message |
| POST | `/conversations/{id}/messages/{mid}/regenerate` | Regenerate |
| POST | `/conversations/{id}/clear` | Clear messages |
| POST | `/conversations/{id}/summary/regenerate` | Manual summary regeneration |
| POST | `/messages/{mid}/feedback` | Human rating + notes |
| POST | `/messages/{mid}/judge` | Manual LLM judge (→ job or sync) |

### SSE Event Types (chat)

```text
event: token
data: {"content": "partial text"}

event: tool_call
data: {"name": "calculator", "arguments": {...}}

event: tool_result
data: {"name": "calculator", "result": "42"}

event: citation
data: {"document_id": "...", "chunk_id": "...", "text": "..."}

event: approval_required
data: {"tool": "...", "arguments": {...}}

event: done
data: {"message_id": "...", "trace_id": "..."}

event: error
data: {"code": "...", "message": "..."}
```

## 6. Traces

| Method | Path | Description |
| --- | --- | --- |
| GET | `/traces/{id}` | Full trace detail |
| GET | `/traces` | List traces (filter: agent, date) |

## 7. Knowledge

| Method | Path | Description |
| --- | --- | --- |
| GET | `/knowledge/collections` | List collections |
| POST | `/knowledge/collections` | Create collection |
| GET | `/knowledge/collections/{id}` | Collection detail |
| PATCH | `/knowledge/collections/{id}` | Update metadata |
| POST | `/knowledge/collections/{id}/ready-check` | Run readiness check |
| POST | `/knowledge/collections/{id}/documents` | Upload document (multipart) |
| GET | `/knowledge/documents/{id}` | Document detail |
| GET | `/knowledge/documents/{id}/text` | Extracted text |
| GET | `/knowledge/documents/{id}/chunks` | Chunk list |
| POST | `/knowledge/documents/{id}/reprocess` | Reprocess (→ job) |
| POST | `/knowledge/documents/{id}/reindex` | Re-embed (→ job) |
| POST | `/knowledge/documents/{id}/archive` | Archive |
| DELETE | `/knowledge/documents/{id}` | Delete |
| POST | `/knowledge/retrieval/debug` | Retrieval debugger query |

## 8. Tools

| Method | Path | Description |
| --- | --- | --- |
| GET | `/tools` | List available tools |
| POST | `/tool-approvals/{id}/approve` | Approve pending tool call |
| POST | `/tool-approvals/{id}/reject` | Reject pending tool call |

## 9. Evaluations

| Method | Path | Description |
| --- | --- | --- |
| GET | `/evaluations/datasets` | List datasets |
| POST | `/evaluations/datasets` | Create dataset |
| GET | `/evaluations/datasets/{id}` | Dataset with versions |
| POST | `/evaluations/datasets/{id}/versions` | Create new version |
| GET | `/evaluations/datasets/{id}/versions/{vid}` | Version with cases |
| POST | `/evaluations/datasets/{id}/versions/{vid}/cases` | Add case |
| PATCH | `/evaluations/cases/{id}` | Update case |
| POST | `/evaluations/datasets/{id}/import` | CSV/JSON import |
| GET | `/evaluations/datasets/{id}/export` | CSV/JSON export |
| POST | `/evaluations/datasets/{id}/generate` | AI test generation (→ job) |
| POST | `/evaluations/runs` | Start evaluation (→ job) |
| GET | `/evaluations/runs/{id}` | Run status + results |
| POST | `/evaluations/runs/{id}/cancel` | Cancel run |
| POST | `/evaluations/results/{id}/review` | Human review |
| POST | `/evaluations/runs/estimate` | Cost estimate (no execution) |

## 10. Judges

| Method | Path | Description |
| --- | --- | --- |
| GET | `/judges/rubrics` | List rubric templates |
| POST | `/judges/multi-review` | Multi-judge review (→ job) |

## 11. Comparisons and Regression

| Method | Path | Description |
| --- | --- | --- |
| POST | `/comparisons` | Start comparison (→ job) |
| GET | `/comparisons/{id}` | Comparison results |
| POST | `/comparisons/{id}/summary` | AI comparison summary (→ job) |
| GET | `/regressions` | List detected regressions |

## 12. Red Team

| Method | Path | Description |
| --- | --- | --- |
| POST | `/red-team/runs` | Start red-team test (→ job) |
| GET | `/red-team/runs/{id}` | Results |
| POST | `/red-team/cases/{id}/promote` | Add to eval dataset |

## 13. Release

| Method | Path | Description |
| --- | --- | --- |
| POST | `/agents/{id}/versions/{vid}/release-check` | Run release check |
| POST | `/agents/{id}/versions/{vid}/mark-release-ready` | Manual mark (after check pass) |

## 14. Templates and Sample Packs

| Method | Path | Description |
| --- | --- | --- |
| GET | `/templates` | List templates |
| GET | `/templates/{id}` | Template detail |
| POST | `/templates/{id}/apply` | Create agent from template |
| GET | `/sample-packs` | List sample packs |
| POST | `/sample-packs/{id}/install` | Install synthetic pack |

## 15. Jobs

| Method | Path | Description |
| --- | --- | --- |
| GET | `/jobs` | List jobs (filter: status, type) |
| GET | `/jobs/{id}` | Job detail + progress |
| POST | `/jobs/{id}/cancel` | Cancel if safe |
| POST | `/jobs/{id}/retry` | Retry failed job |

## 16. Settings

| Method | Path | Description |
| --- | --- | --- |
| GET | `/settings/providers` | Provider config status (no secrets) |
| PUT | `/settings/providers` | Update provider settings |
| GET | `/settings/models` | Model registry |
| GET | `/settings/pricing` | Pricing table |
| PUT | `/settings/pricing` | Update pricing |
| GET | `/settings/security` | Security settings |
| PUT | `/settings/security` | Update limits/thresholds |

## 17. Dashboard and Onboarding

| Method | Path | Description |
| --- | --- | --- |
| GET | `/dashboard` | Aggregated metrics |
| GET | `/onboarding/progress` | Wizard state |
| PUT | `/onboarding/progress` | Save wizard step |
| POST | `/onboarding/complete` | Mark complete |

## 18. Guides and Learning

| Method | Path | Description |
| --- | --- | --- |
| GET | `/guides` | List guides |
| GET | `/guides/{slug}` | Guide content |

## 19. Health

| Method | Path | Description |
| --- | --- | --- |
| GET | `/health` | Liveness |
| GET | `/ready` | Readiness (DB, Redis) |

## 20. Error Response Format

```json
{
  "type": "https://agentlab.local/errors/validation",
  "title": "Validation Error",
  "status": 422,
  "detail": "Retrieval top_k must be between 1 and 20",
  "instance": "/api/v1/agents/.../versions/...",
  "errors": [
    {"field": "retrieval_config.top_k", "message": "..."}
  ]
}
```

## 21. Rate Limiting

| Endpoint group | Limit |
| --- | --- |
| Auth login | 5/min per IP |
| Chat messages | 30/min per user |
| Expensive operations | 10/hour per user |
| File upload | 20/hour per user |

## 22. Export Endpoints

| Method | Path | Description |
| --- | --- | --- |
| POST | `/exports/promptfoo` | Promptfoo-compatible export |

## 23. API Versioning

v1 is the initial version. Breaking changes require v2 with parallel support period documented in CHANGELOG.
