#!/bin/bash
# =============================================================================
# Provaani Production — Automated Health Watchdog & Self-Healing Service
# =============================================================================
# Runs via cron every 5 minutes or as a background service:
# */5 * * * * /home/rahul/Provaani_akruti/deploy/health_monitor.sh >> /var/log/provaani_monitor.log 2>&1
#
# Checks:
#   1. Dograh Backend API endpoint (/api/v1/health)
#   2. Docker containers health status (restarts unhealthy containers automatically)
#   3. Disk capacity (< 85% threshold)
#   4. System RAM capacity
# =============================================================================

set -euo pipefail

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_TAG="[MONITOR ${TIMESTAMP}]"
ALERT=0

# 1. Check API HTTP Health
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:8000/api/v1/health || echo "000")

if [ "${HTTP_STATUS}" != "200" ]; then
    echo "${LOG_TAG} ⚠️  API HEALTH FAILED! HTTP code: ${HTTP_STATUS}"
    ALERT=1
    # Auto-healing: restart API container
    echo "${LOG_TAG} 🔄 Attempting auto-recovery: restarting provaani_akruti-api-1..."
    sudo docker restart provaani_akruti-api-1 || true
fi

# 2. Check Unhealthy Docker Containers
UNHEALTHY_CONTAINERS=$(sudo docker ps --filter "health=unhealthy" --format "{{.Names}}" || true)
if [ -n "${UNHEALTHY_CONTAINERS}" ]; then
    echo "${LOG_TAG} ⚠️  Unhealthy containers detected: ${UNHEALTHY_CONTAINERS}"
    ALERT=1
    for c in ${UNHEALTHY_CONTAINERS}; do
        echo "${LOG_TAG} 🔄 Restarting unhealthy container: ${c}..."
        sudo docker restart "${c}" || true
    done
fi

# 3. Check Disk Usage Threshold
DISK_USAGE_PCT=$(df / | awk 'NR==2 {gsub(/%/,""); print $5}')
if [ "${DISK_USAGE_PCT}" -gt 85 ]; then
    echo "${LOG_TAG} ⚠️  CRITICAL: Root disk usage at ${DISK_USAGE_PCT}% (Threshold: 85%)"
    ALERT=1
    # Auto-prune old docker logs / dangling images if disk is critical
    if [ "${DISK_USAGE_PCT}" -gt 90 ]; then
        echo "${LOG_TAG} 🧹 Running emergency docker system prune..."
        sudo docker system prune -f || true
    fi
fi

# 4. Check Available Memory
AVAIL_MEM_MB=$(free -m | awk '/^Mem:/ {print $7}')
if [ "${AVAIL_MEM_MB}" -lt 300 ]; then
    echo "${LOG_TAG} ⚠️  WARNING: Low available memory: ${AVAIL_MEM_MB}MB available"
    ALERT=1
fi

if [ "${ALERT}" -eq 0 ]; then
    echo "${LOG_TAG} ✅ All systems healthy (API: 200 OK | Disk: ${DISK_USAGE_PCT}% | Mem Avail: ${AVAIL_MEM_MB}MB)"
fi
