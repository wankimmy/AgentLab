#!/usr/bin/env bash
set -euo pipefail
# Backup PostgreSQL from docker compose postgres service.
BACKUP_DIR="${BACKUP_DIR:-./backups}"
mkdir -p "$BACKUP_DIR"
STAMP=$(date +%Y%m%d-%H%M%S)
FILE="$BACKUP_DIR/agentlab-${STAMP}.sql.gz"
docker compose exec -T postgres pg_dump -U "${POSTGRES_USER:-agentlab}" "${POSTGRES_DB:-agentlab}" | gzip > "$FILE"
echo "Wrote $FILE"
# Retain last 7 daily-style backups (simple prune)
ls -1t "$BACKUP_DIR"/agentlab-*.sql.gz 2>/dev/null | tail -n +8 | xargs -r rm -f
