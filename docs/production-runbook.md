# Production Runbook

## Prerequisites

- VPS with Docker (4 vCPU / 8GB RAM recommended)
- DNS `A` record for `DOMAIN` → VPS IP
- GitHub secrets: `VPS_HOST`, `VPS_USER`, `VPS_SSH_KEY`
- Repo `.env` on server with `DOMAIN`, `ACME_EMAIL`, `APP_SECRET_KEY`, database passwords

## First deploy

```bash
git clone <repo> ~/agentlab && cd ~/agentlab
cp .env.example .env
# Edit .env for production secrets
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d --build
./infrastructure/scripts/smoke.sh https://$DOMAIN
```

## Routine deploy

Merge to `production` branch or run **Deploy Production** workflow manually. Workflow:

1. Build/push images to GHCR (`:sha`)
2. SSH: backup DB → pull → migrate → up
3. Smoke health/ready; rollback on failure

## Rollback

```bash
./infrastructure/scripts/rollback.sh
```

Requires `.env.previous` with last known-good `IMAGE_TAG`.

## Hostinger notes

- Open ports 80/443 on firewall
- Point domain to VPS; wait for DNS propagation before ACME
- Keep backups off-box when possible (copy `backups/` to object storage)

See also [backup-and-restore.md](backup-and-restore.md) and [troubleshooting.md](troubleshooting.md).
