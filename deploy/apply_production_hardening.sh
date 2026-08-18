#!/bin/bash
# =============================================================================
# Provaani Production Hardening — One-Shot VM Deployment Script
# =============================================================================
# This script SSHs into the production VM and applies ALL production hardening
# fixes identified in the production readiness audit:
#
#   1. Uploads the new .env with strong passwords
#   2. Uploads the fixed docker-compose.yaml with log rotation
#   3. Uploads the fixed warmup_daemon.py (no hardcoded keys)
#   4. Installs backup, SSL renewal, and logrotate configs
#   5. Sets up all cron jobs
#   6. Restarts the stack with new config
#
# Usage: bash deploy/apply_production_hardening.sh
# =============================================================================

set -euo pipefail

VM_NAME="instance-20260815-072654"
ZONE="asia-south2-b"
PROJECT="project-cb090c10-8c6d-44c8-bbb"
VM_USER="rahul"
APP_DIR="/home/${VM_USER}/Provaani_akruti"

echo "=============================================="
echo "  Provaani Production Hardening Deployment"
echo "=============================================="
echo ""

# --- Step 1: Upload fixed files ---
echo "[1/6] Uploading production configuration files to VM..."

gcloud compute scp \
  .env \
  docker-compose.yaml \
  warmup_daemon.py \
  deploy/backup_db.sh \
  deploy/renew_ssl.sh \
  deploy/health_monitor.sh \
  deploy/provaani-logrotate.conf \
  "${VM_NAME}:${APP_DIR}/" \
  --zone="${ZONE}" --project="${PROJECT}"

echo "  ✅ All files uploaded."

# --- Step 2: Copy warmup_daemon.py into the running API container ---
echo "[2/6] Injecting warmup_daemon.py into API container..."

gcloud compute ssh "${VM_NAME}" --zone="${ZONE}" --project="${PROJECT}" --command="
  sudo docker cp ${APP_DIR}/warmup_daemon.py provaani_akruti-api-1:/app/warmup_daemon.py
"
echo "  ✅ warmup_daemon.py injected."

# --- Step 3: Install logrotate config ---
echo "[3/6] Installing logrotate configuration..."

gcloud compute ssh "${VM_NAME}" --zone="${ZONE}" --project="${PROJECT}" --command="
  sudo cp ${APP_DIR}/deploy/provaani-logrotate.conf /etc/logrotate.d/provaani
  sudo chmod 644 /etc/logrotate.d/provaani
"
echo "  ✅ Logrotate installed."

# --- Step 4: Make scripts executable and set up backup directory ---
echo "[4/6] Setting up backup and monitoring infrastructure..."

gcloud compute ssh "${VM_NAME}" --zone="${ZONE}" --project="${PROJECT}" --command="
  chmod +x ${APP_DIR}/deploy/backup_db.sh ${APP_DIR}/deploy/renew_ssl.sh ${APP_DIR}/deploy/health_monitor.sh
  mkdir -p ${APP_DIR}/backups/postgres
"
echo "  ✅ Infrastructure ready."

# --- Step 5: Install production cron jobs ---
echo "[5/6] Installing production cron jobs..."

gcloud compute ssh "${VM_NAME}" --zone="${ZONE}" --project="${PROJECT}" --command="
  # Build the complete crontab with all production jobs
  (crontab -l 2>/dev/null | grep -v 'warmup_daemon\|cleanup_retention\|backup_db\|renew_ssl\|health_monitor'; cat <<'CRON'
# === Provaani Production Cron Jobs ===
# 24/7 Provider & TLS Warmup Heartbeat (Every 10 minutes)
*/10 * * * * sudo docker exec provaani_akruti-api-1 python3 /app/warmup_daemon.py >> /var/log/provaani_warmup.log 2>&1
# Automated Health Watchdog & Self-Healing (Every 5 minutes)
*/5 * * * * ${APP_DIR}/deploy/health_monitor.sh >> /var/log/provaani_monitor.log 2>&1
# Nightly 3:00 AM Data Retention Cleanup
0 3 * * * sudo docker exec provaani_akruti-api-1 python3 /app/cleanup_retention.py >> /var/log/provaani_cleanup.log 2>&1
# Nightly 2:00 AM PostgreSQL Backup (7-day retention)
0 2 * * * ${APP_DIR}/deploy/backup_db.sh >> /var/log/provaani_backup.log 2>&1
# Weekly Monday 4:00 AM SSL Certificate Renewal
0 4 * * 1 ${APP_DIR}/deploy/renew_ssl.sh >> /var/log/provaani_ssl_renew.log 2>&1
CRON
) | crontab -
  echo 'Installed crontab:'
  crontab -l
"
echo "  ✅ All cron jobs installed."

# --- Step 6: Restart the stack with new configuration ---
echo "[6/6] Restarting Docker stack with production configuration..."
echo ""
echo "  ⚠️  NOTE: Changing database passwords requires manual PostgreSQL ALTER."
echo "  The new .env passwords will take effect for NEW containers."
echo "  Existing PostgreSQL password is baked into the volume on first init."
echo "  To change it, run:"
echo "    sudo docker exec -it provaani_akruti-postgres-1 psql -U postgres -c \"ALTER USER postgres PASSWORD 'NEW_PASSWORD';\""
echo ""

gcloud compute ssh "${VM_NAME}" --zone="${ZONE}" --project="${PROJECT}" --command="
  cd ${APP_DIR}
  sudo docker compose restart
  sleep 5
  echo ''
  echo '=== Container Status ==='
  sudo docker ps --format 'table {{.Names}}\t{{.Status}}'
  echo ''
  echo '=== API Health Check ==='
  curl -s http://localhost:8000/api/v1/health | python3 -c 'import json,sys; d=json.load(sys.stdin); print(\"Status:\", d.get(\"status\"), \"| Version:\", d.get(\"version\"), \"| Mode:\", d.get(\"deployment_mode\"))'
"

echo ""
echo "=============================================="
echo "  ✅ Production Hardening Complete!"
echo "=============================================="
echo ""
echo "Remaining MANUAL steps:"
echo "  1. Set up UptimeRobot/Better Stack to monitor http://34.131.238.156:8000/api/v1/health"
echo "  2. Enable GCP disk snapshots: Console → Compute Engine → Disks → Create Snapshot Schedule"
echo "  3. Change dashboard admin password: Login at https://akruti.provaani.xyz and update"
echo "  4. Add CEREBRAS_API_KEY and SMALLEST_API_KEY to .env on VM for warmup daemon"
echo "  5. Run initial backup: ${APP_DIR}/deploy/backup_db.sh"
echo ""
