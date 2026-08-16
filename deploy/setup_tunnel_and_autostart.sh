#!/usr/bin/env bash
# ==============================================================================
# Provaani Akruti — Cloudflare Named Tunnel & VM Auto-Restart Setup Script
# ==============================================================================
set -euo pipefail

SUBDOMAIN="${1:-}"
TUNNEL_TOKEN="${2:-}"
APP_DIR="${3:-/root/Provaani_akruti}"

if [ -z "$SUBDOMAIN" ] || [ -z "$TUNNEL_TOKEN" ]; then
  echo "Usage: sudo ./setup_tunnel_and_autostart.sh <SUBDOMAIN> <CLOUDFLARE_TUNNEL_TOKEN> [APP_DIR]"
  echo "Example: sudo ./setup_tunnel_and_autostart.sh voice.myclinic.com eyJh..."
  exit 1
fi

echo "=========================================================="
echo "🚀 Configuring Provaani Akruti for Subdomain: $SUBDOMAIN"
echo "=========================================================="

cd "$APP_DIR"

# 1. Update or append environment variables in .env
echo "[1/4] Updating environment configuration (.env)..."

update_or_append_env() {
  local key="$1"
  local val="$2"
  if grep -q "^${key}=" .env 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|" .env
  else
    echo "${key}=${val}" >> .env
  fi
}

touch .env

update_or_append_env "CLOUDFLARE_TUNNEL_TOKEN" "$TUNNEL_TOKEN"
update_or_append_env "CLOUDFLARED_COMMAND" "tunnel run"
update_or_append_env "PUBLIC_BASE_URL" "https://${SUBDOMAIN}"
update_or_append_env "PUBLIC_HOST" "${SUBDOMAIN}"
update_or_append_env "BACKEND_API_ENDPOINT" "https://${SUBDOMAIN}"
update_or_append_env "MINIO_PUBLIC_ENDPOINT" "https://${SUBDOMAIN}"

echo "  -> Configured PUBLIC_BASE_URL=https://${SUBDOMAIN}"
echo "  -> Configured CLOUDFLARE_TUNNEL_TOKEN and command"

# 2. Configure and enable systemd service for 100% reboot survival
echo "[2/4] Configuring systemd auto-start service..."
cat << 'EOF' > /etc/systemd/system/provaani.service
[Unit]
Description=Provaani Akruti Voice Agent Stack (Docker Compose)
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/root/Provaani_akruti
ExecStart=/usr/bin/docker compose --profile tunnel up -d
ExecStop=/usr/bin/docker compose --profile tunnel down
TimeoutStartSec=180

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable docker
systemctl enable provaani.service
echo "  -> provaani.service enabled (stack will auto-boot on VM restart)"

# 3. Launch Docker Compose Stack
echo "[3/4] Starting Docker services with Cloudflare Tunnel..."
docker compose --profile tunnel down || true
docker compose --profile tunnel up -d

# 4. Verification
echo "[4/4] Verifying health and connectivity..."
sleep 5

for i in $(seq 1 12); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    echo "✅ Local API is Healthy (HTTP 200)!"
    break
  fi
  echo "  Waiting for API startup (attempt $i/12)..."
  sleep 4
done

echo ""
echo "=========================================================="
echo "🎉 Setup Complete!"
echo "Public Domain: https://${SUBDOMAIN}"
echo "Plivo Webhook URL to configure in Plivo Console:"
echo "  👉 https://${SUBDOMAIN}/api/v1/telephony/plivo/webhook"
echo "=========================================================="
