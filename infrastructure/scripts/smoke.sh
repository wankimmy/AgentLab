#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-http://localhost:8000}"
BASE="${BASE%/}"
curl -fsS "$BASE/api/v1/health" | grep -q '"status":"ok"' || exit 1
curl -fsS "$BASE/api/v1/ready" | grep -q '"status"' || exit 1
echo "Smoke OK: $BASE"
