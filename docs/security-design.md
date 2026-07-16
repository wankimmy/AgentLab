# Security Design — AgentLab

## 1. Threat Model

AgentLab handles untrusted inputs from three sources:

1. **Users** — authenticated owner and demo account
2. **Uploaded documents** — treated as untrusted content (indirect prompt injection)
3. **Model outputs** — treated as untrusted (XSS, malicious links)

## 2. Authentication and Session

| Control | Implementation |
| --- | --- |
| Password hashing | bcrypt with cost factor 12 |
| Session storage | Server-side session with secure cookie |
| Cookie flags | HttpOnly, Secure (production), SameSite=Lax |
| Session expiry | 24 hours (configurable) |
| Brute force protection | Rate limit login: 5 attempts/min per IP |
| Demo account | Read-only; cannot trigger expensive operations |

No public registration. Owner account seeded at deploy.

## 3. Authorization

| Role | Permissions |
| --- | --- |
| owner | Full CRUD, all operations |
| demo | Read-only; no create/edit/delete; no expensive ops |

All API endpoints require authentication except `/health`, `/ready`, `/auth/login`.

## 4. Input Validation

| Vector | Control |
| --- | --- |
| SQL injection | Parameterised queries (SQLAlchemy); no raw SQL from user input |
| XSS | Sanitise Markdown rendering; CSP headers; no `v-html` without sanitiser |
| CSRF | SameSite cookies; CSRF token on state-changing requests if needed |
| Path traversal | Sanitise filenames; store with internal UUID names |
| Oversized requests | Body size limit (10MB default); file size limit (20MB) |
| Malicious uploads | MIME validation; never execute uploaded files |

## 5. AI-Specific Security

| Threat | Mitigation |
| --- | --- |
| Prompt injection (direct) | System prompt hardening; security test cases; red-team suite |
| Indirect prompt injection (RAG) | Separate system vs retrieved content; delimiter blocks; explicit rules |
| Tool abuse | Tool allowlist; step/call limits; approval mode; audit logs |
| Arbitrary code execution | No eval(); safe calculator parser only |
| Arbitrary URL access | No HTTP tools in MVP |
| Arbitrary SQL | No SQL tools in MVP |
| Secret extraction | Secrets never in prompts; log redaction |
| Excessive tool use | max_tool_calls per turn |
| DoS via long input | Input length limits; timeout enforcement |
| Unbounded spending | Cost limits; batch caps; hard stop thresholds |

## 6. Secret Management

| Rule | Detail |
| --- | --- |
| Provider API keys | Environment variables only; server-side |
| Never in frontend | Keys not in API responses, logs, or client code |
| Never in git | `.env` in `.gitignore`; `.env.example` with placeholders |
| Never in exports | Export endpoints strip secrets |
| Log redaction | Middleware redacts keys, tokens, passwords |

## 7. Network Security

| Control | Detail |
| --- | --- |
| HTTPS | Traefik TLS termination; HTTP redirects to HTTPS |
| CORS | Strict origin allowlist (frontend domain only) |
| Internal services | PostgreSQL, Redis, MLflow on private Docker network |
| Security headers | HSTS, X-Content-Type-Options, X-Frame-Options, CSP |
| Rate limiting | Per-endpoint limits (see API design) |

## 8. Output Safety

| Control | Detail |
| --- | --- |
| Markdown rendering | Safe renderer (no raw HTML injection) |
| Model-generated links | `rel="noopener noreferrer"`; optional domain allowlist |
| No chain-of-thought | Runtime does not expose hidden reasoning |
| Error messages | No stack traces to client in production |

## 9. Audit Logging

Log to `audit_logs` table:

| Action | Details logged |
| --- | --- |
| auth.login | user_id, IP, success/fail |
| auth.logout | user_id |
| agent.create/update/delete | agent_id, changes |
| version.create/activate | version_id |
| tool.execute | tool name, args (sanitized), result status |
| tool.approve/reject | approval_id, decision |
| eval.start/complete | run_id, mode, cost |
| release.mark_ready | version_id, check results |
| settings.update | changed fields (no secrets) |
| document.upload/delete | document_id |
| red_team.start | run_id, categories |

Retention: 90 days default (configurable).

## 10. Spending Controls

| Control | Default |
| --- | --- |
| max_cost_per_evaluation | $5.00 |
| max_daily_cost | $20.00 |
| warning_threshold | 80% |
| hard_stop | 100% |
| max_test_cases_per_run | 50 |
| max_judge_calls | 100 |
| max_concurrent_jobs | 3 |

## 11. Background Job Security

- Idempotency keys prevent duplicate expensive operations.
- Job arguments validated before enqueue.
- Cancel only safe jobs (not mid-provider-call).
- Failed jobs do not retry provider calls automatically.

## 12. Data Protection

- Single-owner portfolio project; no multi-tenant isolation required.
- Uploaded documents stored on server volume with restricted permissions.
- Database backups encrypted at rest (VPS provider dependent).
- No PII in synthetic sample data.

## 13. Security Testing

| Test | Phase |
| --- | --- |
| Auth bypass attempts | Phase 1 |
| CSRF validation | Phase 1 |
| XSS in Markdown rendering | Phase 3 |
| Path traversal on upload | Phase 4 |
| Tool allowlist enforcement | Phase 5 |
| Prompt injection red-team | Phase 9 |
| Rate limit verification | Phase 1 |
| Secret exposure scan (CI) | Phase 1 |

## 14. Incident Response (Portfolio)

Documented in `docs/troubleshooting.md`:

1. Rotate provider API keys if exposed.
2. Review audit logs for suspicious activity.
3. Disable demo account if compromised.
4. Restore from backup if data corruption.

## 15. Security Headers (Traefik middleware)

```text
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'
```
