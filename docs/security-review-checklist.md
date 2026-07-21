# Security Review Checklist — Phase 11

Reference: [security-design.md](security-design.md). Marked against current implementation.

## Authentication and sessions

- [x] HttpOnly session cookies
- [x] `secure` cookie flag when `APP_ENV=production`
- [x] Login rate limiting (Redis)
- [x] Demo account read-only via middleware + role in session

## Authorization

- [x] Single-owner model; demo cannot POST/PATCH/DELETE (except auth)
- [ ] Fine-grained per-route `WriteUser` dependency (middleware covers MVP)

## Data and secrets

- [x] Secrets via environment variables (`.env` not committed)
- [x] No API keys in logs (structured logging avoids full prompts in prod policy)
- [x] CI pip-audit step (non-blocking report)

## Network and deploy

- [x] Production compose removes public DB/Redis ports
- [x] Traefik TLS termination with Let's Encrypt
- [ ] WAF / CDN (operator responsibility on VPS)

## Application security

- [x] Red-team synthetic cases (Phase 9)
- [x] Tool allowlist and approval modes
- [x] RAG delimiter / refusal eval cases

## Operations

- [x] Backup script documented and used in deploy workflow
- [x] Rollback script documented
- [x] Runbook and troubleshooting docs

## Follow-ups (post-MVP)

- [ ] Automated gitleaks in CI (optional hardening)
- [ ] OWASP ZAP scan on staging
- [ ] Per-tenant isolation (out of scope for portfolio)

**Reviewed:** Phase 11 implementation pass (in-repo controls verified; live VPS drill is operator-run).
