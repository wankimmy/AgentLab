# AgentLab — Portfolio Case Study

## Problem

Teams need a repeatable way to build, evaluate, and release AI agents—not only a chat UI. AgentLab demonstrates an end-to-end workflow from templates and knowledge through evaluation, comparison, security testing, and release gates.

## Solution

A modular monolith (FastAPI + Nuxt) with:

- Session-based auth for a single owner plus optional read-only demo
- RAG over user-uploaded knowledge with trace visibility
- Deterministic and LLM-judge metrics on evaluation datasets
- Regression comparison between agent versions
- Red-team and prompt-improvement tooling

## Architecture highlights

- **Native runtime first** (ADR-002); LangGraph adapter for optional stateful graphs
- **Product traces** (`chat_traces`) separate from **OpenTelemetry** operational spans
- **Mock providers** in CI to avoid API cost and flakiness
- **Celery** for document processing and long eval runs

## What this demonstrates

- Applied ML engineering: datasets, metrics, judges, MLflow experiment logging
- Security awareness: synthetic red-team, demo read-only, session hardening
- DevOps: Docker Compose dev/prod, Traefik TLS, backup/rollback scripts, GitHub Actions

## Honest limits

- Single-tenant; no multi-org RBAC
- Performance numbers depend on your VPS and provider; no benchmark claims are made here
- Production HTTPS requires your domain, DNS, and VPS secrets (see runbook)
