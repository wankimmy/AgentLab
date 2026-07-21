#!/usr/bin/env bash
set -euo pipefail
# Roll back to previous IMAGE_TAG recorded in .env.previous
if [[ ! -f .env.previous ]]; then
  echo "No .env.previous found; set IMAGE_TAG manually and redeploy."
  exit 1
fi
cp .env.previous .env
docker compose -f docker-compose.yml -f docker-compose.production.yml pull
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d
"$(dirname "$0")/smoke.sh" "https://${DOMAIN}"
