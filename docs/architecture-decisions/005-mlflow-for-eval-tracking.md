# ADR-005: MLflow for Evaluation Tracking

## Status

Accepted

## Context

AgentLab needs to track evaluation experiments with parameters, metrics, and artifacts across agent versions, prompts, models, and datasets. Results must be reproducible.

## Decision

Use **self-hosted MLflow** on the internal Docker network for evaluation experiment tracking. Not exposed publicly.

## Consequences

**Positive:**
- Industry-standard experiment tracking
- Parameters, metrics, and artifacts in one place
- Comparison across runs built-in
- Demonstrates MLOps skills for portfolio

**Negative:**
- Additional container and storage
- MLflow UI not user-facing (product has its own eval UI)

**Mitigation:** Product UI is primary; MLflow is backend tracking. Artifacts also stored in PostgreSQL.
