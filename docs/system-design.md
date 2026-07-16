# System Design — AgentLab

## 1. Architecture Overview

AgentLab is a **modular monolith** deployed as separate containers via Docker Compose. Business logic lives in one FastAPI codebase with clear module boundaries. Workers share the same codebase and database.

```mermaid
flowchart TB
  subgraph client [Client]
    Browser[Nuxt_Web_App]
  end

  subgraph edge [Edge]
    Traefik[Traefik_HTTPS]
  end

  subgraph app [Application]
    API[FastAPI_API]
    Worker[Celery_Workers]
    Runtime[Native_Agent_Runtime]
  end

  subgraph data [Data]
    PG[(PostgreSQL_pgvector)]
    Redis[(Redis)]
    FS[File_Storage]
    MLflow[MLflow]
  end

  subgraph external [External]
    LLM[LLM_Providers]
  end

  Browser --> Traefik
  Traefik --> API
  API --> Runtime
  API --> PG
  API --> Redis
  API --> FS
  API --> MLflow
  Worker --> PG
  Worker --> Redis
  Worker --> FS
  Worker --> MLflow
  Runtime --> LLM
  Worker --> LLM
```

## 2. Repository Structure

```text
agentlab/
├── apps/
│   ├── web/                 # Nuxt 4 frontend
│   └── api/                 # FastAPI backend
│       └── app/
│           ├── api/         # Route handlers
│           ├── authentication/
│           ├── agents/
│           ├── agent_versions/
│           ├── prompts/
│           ├── conversations/
│           ├── providers/
│           ├── runtime/
│           ├── knowledge/
│           ├── retrieval/
│           ├── tools/
│           ├── evaluations/
│           ├── judges/
│           ├── comparisons/
│           ├── templates/
│           ├── jobs/
│           ├── observability/
│           ├── models/      # SQLAlchemy models
│           ├── schemas/     # Pydantic schemas
│           ├── repositories/
│           ├── services/
│           └── core/        # Config, deps, security
├── workers/                 # Celery app entry
├── infrastructure/
│   ├── docker/
│   ├── monitoring/
│   └── scripts/
├── docs/
├── tests/
├── seed/
├── sample-packs/
├── docker-compose.yml
├── docker-compose.production.yml
└── .env.example
```

## 3. Component Responsibilities

| Component | Responsibility |
| --- | --- |
| **Nuxt Web** | UI, SSE client, auth cookie handling, form validation |
| **FastAPI API** | REST + SSE endpoints, auth, orchestration, sync operations |
| **Native Runtime** | Agent loop: prompt assembly, retrieval, tool calls, streaming |
| **Celery Workers** | Document processing, embeddings, batch eval, judge, red-team |
| **PostgreSQL** | Source of truth for all product state |
| **pgvector** | Vector similarity search |
| **Redis** | Celery broker, rate-limit counters, session cache (optional) |
| **File Storage** | Uploaded documents, exports, MLflow artifacts path |
| **MLflow** | Evaluation experiment tracking (internal network only) |
| **Traefik** | TLS termination, routing, health checks |

## 4. Request Flows

### 4.1 Chat request (playground)

```mermaid
sequenceDiagram
  participant U as User
  participant W as Nuxt
  participant A as FastAPI
  participant R as Runtime
  participant Ret as Retrieval
  participant P as Provider
  participant DB as PostgreSQL

  U->>W: Send message
  W->>A: POST /conversations/{id}/messages (SSE)
  A->>DB: Load agent version + conversation
  A->>R: Execute turn
  R->>Ret: Retrieve context if RAG enabled
  Ret->>DB: Vector + keyword search
  Ret-->>R: Chunks + citations
  R->>P: Stream chat completion
  P-->>R: Tokens + tool calls
  alt Tool call
    R->>R: Execute or request approval
  end
  R-->>A: Stream events
  A-->>W: SSE chunks
  A->>DB: Persist message + trace
  W-->>U: Render response + trace
```

### 4.2 Agent onboarding flow

```mermaid
flowchart TD
  Start[UserStartsOnboarding] --> Define[SaveAgentDefinition]
  Define --> Template[SelectTemplate]
  Template --> CreateAgent[CreateAgentAndVersion]
  CreateAgent --> Prompt[ApplyPromptTemplate]
  Prompt --> Knowledge[AttachOrSkipKnowledge]
  Knowledge --> Tools[ConfigureTools]
  Tools --> Cases[CreateStarterCases]
  Cases --> Playground[OpenPlayground]
  Playground --> QuickEval[RecommendQuickCheck]
  QuickEval --> Complete[MarkOnboardingComplete]
```

### 4.3 Background job flow

```mermaid
flowchart TD
  API[APIReceivesRequest] --> Validate[ValidateAndEstimateCost]
  Validate --> Enqueue[EnqueueCeleryTask]
  Enqueue --> Redis[(Redis)]
  Redis --> Worker[CeleryWorker]
  Worker --> Execute[ExecuteJob]
  Execute --> Update[UpdateJobStatusInDB]
  Update --> Notify[ClientPollsOrSSEProgress]
  Execute -->|Failure| Retry[LimitedRetry]
  Retry --> Update
```

## 5. Module Boundaries

Each FastAPI module owns:

- SQLAlchemy models (or re-exports from `models/`)
- Pydantic request/response schemas
- Repository (data access)
- Service (business logic)
- Router (HTTP handlers)

Cross-module communication goes through service interfaces, not direct model access from routers.

## 6. Runtime Architecture

```mermaid
flowchart LR
  Input[UserMessage] --> Assembler[ContextAssembler]
  Assembler --> System[SystemPrompt]
  Assembler --> History[ConversationHistory]
  Assembler --> RAG[RetrievedContext]
  Assembler --> Tools[ToolDefinitions]
  Assembler --> LLM[ProviderChatCall]
  LLM -->|ToolCall| Executor[ToolExecutor]
  Executor -->|Result| LLM
  LLM --> Output[StreamedResponse]
  Output --> Trace[TraceRecorder]
```

**Step limits:** `max_agent_steps`, `max_tool_calls`, `timeout` enforced in runtime loop.

## 7. Evaluation Engine

```mermaid
flowchart TD
  Start[StartEvalRun] --> Load[LoadDatasetVersion]
  Load --> ForEach[ForEachTestCase]
  ForEach --> Invoke[InvokeAgentRuntime]
  Invoke --> Det[DeterministicMetrics]
  Det --> Sem[SemanticSimilarity]
  Sem --> RAGm[RAGMetrics]
  RAGm --> ToolM[ToolMetrics]
  ToolM --> Judge{JudgeEnabled?}
  Judge -->|Yes| LLMJ[LLMJudge]
  Judge -->|No| Aggregate
  LLMJ --> Aggregate[AggregateResults]
  Aggregate --> MLflow[LogToMLflow]
  Aggregate --> Done[CompleteRun]
```

## 8. Technology Versions

| Component | Version |
| --- | --- |
| Nuxt | 4.4.x |
| Python | 3.12 |
| FastAPI | 0.139.x |
| PostgreSQL | 16 |
| pgvector | 0.8.x |
| Redis | 7.x |
| Celery | 5.x |

## 9. Deployment Topology (Production)

```mermaid
flowchart TB
  Internet[Internet] --> Traefik[Traefik_VPS]
  Traefik --> Web[Nuxt_Container]
  Traefik --> API[FastAPI_Container]
  API --> PG[(PostgreSQL)]
  API --> Redis[(Redis)]
  Worker[Celery_Container] --> PG
  Worker --> Redis
  API --> MLflow[MLflow_Internal]
  Worker --> MLflow
  PG --> Backup[BackupVolume]
```

Public: HTTPS on 443 only.
Internal network: PostgreSQL, Redis, MLflow not exposed.

## 10. Future Extensions (Documented, Not MVP)

- LangGraph runtime adapter (Phase 10)
- OpenTelemetry exporters to Langfuse/Phoenix
- CrewAI multi-agent adapter

## 11. Key Design Constraints

1. Provider API keys never reach the browser.
2. Historical agent versions are immutable.
3. Deterministic failures cannot be overridden by judge scores.
4. Expensive operations are always manual with cost preview.
5. Uploaded documents are untrusted content (RAG safety).
