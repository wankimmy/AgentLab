# Backup and Restore

## Backup

```bash
./infrastructure/scripts/backup-db.sh
```

Writes `backups/agentlab-<timestamp>.sql.gz`. Retains the 7 most recent files in `backups/` (simple local prune).

Schedule on VPS with cron, e.g. daily at 02:00 UTC.

## Restore

**Warning:** Overwrites current database contents.

```bash
./infrastructure/scripts/restore-db.sh backups/agentlab-YYYYMMDD-HHMMSS.sql.gz
```

## Pre-deploy backup

The deploy workflow runs `backup-db.sh` before migrations. Keep `.env.previous` for image rollback.

## Off-site retention

Copy gzip dumps to S3-compatible storage or another host; encryption at rest depends on your provider.
