# Troubleshooting

## API `/ready` degraded

- **database: false** — Postgres not healthy; `docker compose logs postgres`
- **redis: false** — Redis down or wrong `REDIS_URL`

## Migrations fail on deploy

- Restore from latest backup before retrying destructive migration
- Run manually: `docker compose run --rm api alembic upgrade head`

## Traefik / HTTPS

- ACME needs port 80 reachable for HTTP challenge
- Check `docker compose logs traefik` for certificate errors
- Verify `DOMAIN` matches DNS and router Host rule

## Celery worker idle / jobs stuck

- Confirm `worker` service running and Redis reachable
- In test env, `task_always_eager` runs inline

## Demo user cannot mutate

- Expected: demo role is read-only except login/logout
- Login again after deploy so session includes `role` in token

## High API cost

- Confirm `AI_API_KEY` not set in CI
- Use MockProvider for demos; run evals on small datasets first
