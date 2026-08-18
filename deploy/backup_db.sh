#!/bin/bash
# Provaani Production — Nightly PostgreSQL Backup
# Run via cron: 0 2 * * * /home/rahul/Provaani_akruti/deploy/backup_db.sh >> /var/log/provaani_backup.log 2>&1
#
# Keeps the last 7 daily backups. Older backups are automatically pruned.

set -euo pipefail

BACKUP_DIR="/home/rahul/Provaani_akruti/backups/postgres"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/provaani_db_${TIMESTAMP}.sql.gz"

# Ensure backup directory exists
mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting PostgreSQL backup..."

# Dump the database from inside the postgres container, compress with gzip
docker exec provaani_akruti-postgres-1 \
  pg_dump -U postgres -d postgres --no-owner --no-privileges \
  | gzip > "${BACKUP_FILE}"

BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
echo "[$(date)] Backup created: ${BACKUP_FILE} (${BACKUP_SIZE})"

# Prune old backups beyond retention period
DELETED=$(find "${BACKUP_DIR}" -name "provaani_db_*.sql.gz" -mtime +${RETENTION_DAYS} -print -delete | wc -l)
echo "[$(date)] Pruned ${DELETED} backup(s) older than ${RETENTION_DAYS} days."

echo "[$(date)] Backup completed successfully."
