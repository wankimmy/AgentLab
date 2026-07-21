# Interview Prep — AgentLab

## Elevator pitch (30s)

AgentLab is a portfolio platform for building and **evaluating** AI agents: RAG, tools, eval datasets, LLM judges, version comparison, and release checks—with production-minded observability and deploy scripts.

## ADRs to cite

| ADR | One line |
| --- | --- |
| 001 Modular monolith | One deployable unit; clear module boundaries |
| 002 Native runtime first | LangGraph optional per version |
| 003 Session auth | Owner + demo; no JWT in localStorage |
| 005 MLflow | Eval experiment tracking |
| 006 OpenAI-compatible providers | Swap models via config |

## Tradeoffs you can defend

- **Monolith vs microservices:** Faster delivery for solo portfolio; Postgres + Redis scale vertically on VPS
- **Deterministic metrics vs judge:** Judges are expensive and noisy; deterministic gates for CI
- **ChatTrace vs OTel:** User-facing trace panel vs SRE backends (Prometheus/OTLP)

## Demo flow (5 min)

1. Login as owner; show ERP sample pack install (synthetic)
2. Playground with mock provider; open trace panel
3. Run Quick Check eval; show pass/fail
4. Compare two versions; release check
5. Mention demo read-only account for reviewers

## Questions you might get

- *How do you prevent prompt injection?* Delimiters, refusal cases, red-team pack, eval gates
- *How do you control cost?* Estimates before expensive ops; mock in CI; rate limits on login
- *How would you scale?* Worker pool, read replicas, external object storage—documented as post-MVP
