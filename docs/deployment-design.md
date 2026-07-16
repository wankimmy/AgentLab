# Deployment Design — AgentLab

## 1. Target Environment

- **Platform:** Hostinger VPS (Linux)
- **Orchestration:** Docker Compose
- **TLS:** Traefik with Let's Encrypt
- **Registry:** GitHub Container Registry (GHCR)
- **CI/CD:** GitHub Actions

## 2. Container Architecture

```mermaid
flowchart TB
  subgraph public_net [Public]
    Traefik[Traefik:443]
  end

  subgraph app_net [Application Network]
    Web[Nuxt:3000]
    API[FastAPI:8000]
    Worker[CeleryWorker]
  end

  subgraph data_net [Data Network]
    PG[PostgreSQL:5432]
    Redis[Redis:6379]
    MLflow[MLflow:5000]
  end

  Traefik --> Web
  Traefik --> API
  API --> PG
  API --> Redis
  Worker --> PG
  Worker --> Redis
  API --> MLflow
  Worker --> MLflow
```

## 3. Services

| Service | Image | Ports | Resources |
| --- | --- | --- | --- |
| traefik | traefik:v3 | 80, 443 | 128MB RAM |
| web | ghcr.io/user/agentlab-web:tag | internal 3000 | 512MB RAM |
| api | ghcr.io/user/agentlab-api:tag | internal 8000 | 1GB RAM |
| worker | ghcr.io/user/agentlab-worker:tag | — | 1GB RAM |
| postgres | pgvector/pgvector:0.8.5-pg16 | internal 5432 | 1GB RAM |
| redis | redis:7-alpine | internal 6379 | 256MB RAM |
| mlflow | ghcr.io/user/agentlab-mlflow:tag | internal 5000 | 512MB RAM |

## 4. Volumes

| Volume | Mount | Purpose |
| --- | --- | --- |
| pgdata | /var/lib/postgresql/data | Database persistence |
| uploads | /app/uploads | Document storage |
| mlflow_artifacts | /mlflow/artifacts | Experiment artifacts |
| traefik_certs | /letsencrypt | TLS certificates |

## 5. Networks

| Network | Services | External access |
| --- | --- | --- |
| public | traefik | Yes (443) |
| app | web, api, worker, traefik | Via traefik only |
| data | postgres, redis, mlflow, api, worker | No |

## 6. Environment Variables

See `.env.example` (created in Phase 1). Key groups:

```text
# App
APP_ENV=production
APP_SECRET_KEY=
APP_DOMAIN=agentlab.example.com

# Database
DATABASE_URL=postgresql://agentlab:password@postgres:5432/agentlab

# Redis
REDIS_URL=redis://redis:6379/0

# AI Providers
AI_BASE_URL=
AI_API_KEY=
AI_DEFAULT_MODEL=
EMBEDDING_BASE_URL=
EMBEDDING_API_KEY=
EMBEDDING_MODEL=
JUDGE_BASE_URL=
JUDGE_API_KEY=
JUDGE_MODEL=

# MLflow
MLFLOW_TRACKING_URI=http://mlflow:5000

# Auth
OWNER_EMAIL=
OWNER_PASSWORD=

# Limits
MAX_DAILY_COST=20.00
MAX_COST_PER_EVAL=5.00
```

## 7. Production Deployment Flow

```mermaid
flowchart TD
  Merge[MergeToProductionBranch] --> CI[RunAllChecks]
  CI --> Build[BuildVersionedImages]
  Build --> Push[PushToGHCR]
  Push --> Backup[BackupDatabase]
  Backup --> SSH[SSHToVPS]
  SSH --> Pull[PullVersionedImages]
  Pull --> Migrate[RunMigrations]
  Migrate --> Start[StartUpdatedServices]
  Start --> Ready[ReadinessChecks]
  Ready --> Smoke[SmokeTests]
  Smoke -->|Pass| Live[TrafficLive]
  Smoke -->|Fail| Rollback[RollbackToPreviousTag]
```

## 8. Docker Compose Files

| File | Purpose |
| --- | --- |
| `docker-compose.yml` | Development (all services, hot reload) |
| `docker-compose.production.yml` | Production overrides (resources, restart, no debug) |

Development exposes ports directly. Production exposes only Traefik on 443.

## 9. Traefik Configuration

```text
# Routes
agentlab.example.com          → web:3000
agentlab.example.com/api      → api:8000 (strip /api prefix)

# TLS
certificatesResolvers.letsencrypt.acme.email = admin@example.com
certificatesResolvers.letsencrypt.acme.storage = /letsencrypt/acme.json
```

## 10. Health Checks

```yaml
# api
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
  interval: 30s
  timeout: 5s
  retries: 3

# postgres
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U agentlab"]
  interval: 10s
  timeout: 5s
  retries: 5
```

## 11. Backup and Restore

### Backup (daily cron on VPS)

```bash
# infrastructure/scripts/backup-db.sh
docker exec postgres pg_dump -U agentlab agentlab | gzip > /backups/agentlab-$(date +%Y%m%d).sql.gz
# Retain 7 daily, 4 weekly
```

### Restore

```bash
# infrastructure/scripts/restore-db.sh
gunzip -c /backups/agentlab-YYYYMMDD.sql.gz | docker exec -i postgres psql -U agentlab agentlab
```

Documented in `docs/backup-and-restore.md` (Phase 11).

## 12. Rollback

1. Note current image tag from deployment.
2. Set `IMAGE_TAG` to previous known-good tag in `.env`.
3. `docker compose -f docker-compose.yml -f docker-compose.production.yml up -d`.
4. Run readiness checks.
5. If DB migration was destructive, restore from pre-deploy backup.

## 13. GitHub Actions

### Pull request workflow

- Python: ruff format, ruff lint, mypy, pytest
- Frontend: eslint, typecheck, vitest, build
- Migration validation
- Secret scanning (gitleaks)
- Container build (no push)

### Production deploy workflow

Triggered on merge to `production` branch:

1. Run all PR checks
2. Build and tag images (`:sha`, `:latest` not used alone)
3. Push to GHCR
4. SSH to VPS, pull images, backup, migrate, restart
5. Readiness + smoke tests
6. Rollback on failure

## 14. Resource Limits (Hostinger VPS)

Typical VPS: 4 vCPU, 8GB RAM. Allocation:

| Service | CPU | RAM |
| --- | --- | --- |
| traefik | 0.25 | 128M |
| web | 0.5 | 512M |
| api | 1.0 | 1G |
| worker | 1.0 | 1G |
| postgres | 1.0 | 2G |
| redis | 0.25 | 256M |
| mlflow | 0.5 | 512M |
| OS overhead | — | ~2G |

## 15. Not Publicly Exposed

- PostgreSQL (port 5432)
- Redis (port 6379)
- MLflow (port 5000)
- Prometheus /metrics endpoint
- Celery Flower (if added)

## 16. Production Runbook

Created in Phase 11 as `docs/production-runbook.md`:

- Deploy procedure
- Rollback procedure
- Backup verification
- Key rotation
- Log investigation
- Cost investigation
- Common failure recovery
