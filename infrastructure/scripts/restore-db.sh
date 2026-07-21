#!/usr/bin/env bash
set -euo pipefail
# Restore from gzip dump: ./restore-db.sh backups/agentlab-YYYYMMDD-HHMMSS.sql.gz
DUMP="${1:?Usage: restore-db.sh <dump.sql.gz>}"
gunzip -c "$DUMP" | docker compose exec -T postgres psql -U "${POSTGRES_USER:-agentlab}" "${POSTGRES_DB:-agentlab}"
echo "Restore completed from $DUMP"
