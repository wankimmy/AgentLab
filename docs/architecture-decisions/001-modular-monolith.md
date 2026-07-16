# ADR-001: Modular Monolith Architecture

## Status

Accepted

## Context

AgentLab is a portfolio project built by a single developer. It has many subsystems (RAG, evaluation, judge, tools) but does not yet have scale requirements that justify microservices.

## Decision

Use a **modular monolith**: one FastAPI codebase with clear module boundaries, deployed as separate containers (API, worker, web) via Docker Compose.

## Consequences

**Positive:**
- Simple development and debugging
- Single database transaction boundary
- Shared code between API and workers
- Easy to deploy on a single VPS

**Negative:**
- Cannot scale API and workers independently beyond container replicas
- All modules share the same deployment cycle

**Mitigation:** Module boundaries via services/repositories allow future extraction if needed.
