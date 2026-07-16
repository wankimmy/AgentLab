# ADR-003: Session Auth for Single Owner

## Status

Accepted

## Context

AgentLab is a personal portfolio project with one primary user and an optional read-only demo account. No teams, organisations, or public registration.

## Decision

Use **server-side session cookies** (HttpOnly, Secure, SameSite=Lax) with bcrypt password hashing. No JWT in localStorage. No OAuth/SSO.

## Consequences

**Positive:**
- Simple auth model matching single-user scope
- Cookies are HttpOnly (XSS-resistant for token theft)
- No token refresh complexity

**Negative:**
- Not suitable for multi-tenant or API-only clients without session
- Session state requires server-side storage or signed cookies

**Mitigation:** If API-only access needed later, add API key auth as separate ADR.
