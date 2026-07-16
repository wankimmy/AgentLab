# ADR-002: Native Runtime First

## Status

Accepted

## Context

AgentLab needs an agent execution loop supporting prompts, RAG, tools, streaming, and limits. LangGraph and CrewAI are available but add complexity and dependencies.

## Decision

Build a **native agent runtime** for MVP. LangGraph adapter is Phase 10 optional. CrewAI is documented as future-only.

## Consequences

**Positive:**
- Understandable and testable execution loop
- No framework lock-in for core product
- Faster MVP delivery

**Negative:**
- No stateful workflow graphs in MVP
- Must implement step limits, approval, and retry logic manually

**Mitigation:** Runtime adapter interface allows LangGraph swap per agent version in Phase 10.
