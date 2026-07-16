# ADR-004: Celery for Expensive Background Jobs

## Status

Accepted

## Context

AgentLab has operations that take seconds to minutes: document processing, embedding generation, batch evaluations, LLM judging, red-team testing, and AI-generated test cases. These cannot block HTTP requests.

## Decision

Use **Redis + Celery** for all expensive background operations. API enqueues jobs; workers execute; client polls or receives SSE progress.

## Consequences

**Positive:**
- Production-ready job queue with retry, visibility, and cancellation
- Same Python codebase shared with API
- Well-documented deployment pattern

**Negative:**
- Additional infrastructure (Redis container)
- Celery configuration complexity

**Mitigation:** Job dashboard in UI; idempotency keys; resource limits per worker.
