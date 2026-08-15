#!/usr/bin/env bash
# Startup script for GCP VM - runs automatically on first boot
set -euo pipefail

exec > /var/log/dograh-startup.log 2>&1
echo "=== Dograh Startup Script: $(date) ==="

# ─── 1. Install Docker ────────────────────────────────────────────
echo "Installing Docker..."
apt-get update -qq
apt-get install -y -qq ca-certificates curl git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update -qq
apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start Docker
systemctl enable docker
systemctl start docker

# ─── 2. Clone repo ────────────────────────────────────────────────
echo "Cloning repo..."
cd /root
if [ -d "dograh_test" ]; then
  cd dograh_test && git pull
else
  git clone https://github.com/Rahulm043/dograh_test.git
  cd dograh_test
fi

# ─── 3. Create .env if missing ────────────────────────────────────
if [ ! -f ".env" ]; then
  echo "Generating .env..."
  cat > .env << 'ENVEOF'
OSS_JWT_SECRET=$(openssl rand -hex 32)
POSTGRES_PASSWORD=$(openssl rand -hex 32)
REDIS_PASSWORD=$(openssl rand -hex 32)
MINIO_ROOT_USER=dograh$(openssl rand -hex 6)
MINIO_ROOT_PASSWORD=$(openssl rand -hex 32)
DEFAULT_ORG_CONCURRENCY_LIMIT=5
FASTAPI_WORKERS=1
ENVIRONMENT=local
ENVEOF
fi

# ─── 4. Build and start ───────────────────────────────────────────
echo "Building custom images (patched API + custom UI)..."
docker compose build api custom-ui 2>&1 || echo "Build failed, continuing..."

echo "Starting stack..."
docker compose --profile tunnel up -d 2>&1

echo "Waiting for health check..."
for i in $(seq 1 15); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health 2>/dev/null || echo "000")
  if [ "$STATUS" = "200" ]; then
    echo "API is healthy!"
    break
  fi
  sleep 5
done

echo "=== Dograh startup complete: $(date) ==="
