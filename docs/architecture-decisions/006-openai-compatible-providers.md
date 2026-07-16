# ADR-006: OpenAI-Compatible Provider Abstraction

## Status

Accepted

## Context

AgentLab must support multiple LLM providers without hard-coding one vendor. The portfolio owner may use OpenAI, Anthropic via proxy, local models, or other compatible APIs.

## Decision

Use an **OpenAI-compatible HTTP adapter** as the primary provider interface. Separate env var groups for chat (`AI_*`), embeddings (`EMBEDDING_*`), and judge (`JUDGE_*`). Mock provider for CI.

## Consequences

**Positive:**
- Works with OpenAI, Azure OpenAI, local vLLM, LiteLLM proxy, etc.
- Judge model independently configured from agent model
- CI runs without paid API calls via MockProvider

**Negative:**
- Non-OpenAI-native features (e.g. Anthropic-specific) require adapter extensions
- Structured output support varies by provider

**Mitigation:** Model capability registry documents per-model features. Graceful errors when capability unsupported.
