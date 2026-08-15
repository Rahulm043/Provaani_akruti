#!/usr/bin/env bash
set -euo pipefail

echo "=== 1. Updating packages and expanding disk ==="
sudo apt-get update
sudo apt-get install -y ca-certificates curl git cloud-guest-utils python3 python3-pip

sudo growpart /dev/sda 1 || true
sudo resize2fs /dev/sda1 || true
df -h /

echo "=== 2. Setting up 4GB Swap file ==="
if [ ! -f /swapfile ]; then
  sudo fallocate -l 4G /swapfile || sudo dd if=/dev/zero of=/swapfile bs=1M count=4096
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
fi
free -h

echo "=== 3. Installing Docker ==="
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
  sudo sh /tmp/get-docker.sh
  sudo usermod -aG docker $USER || true
fi
sudo systemctl enable docker
sudo systemctl start docker

echo "=== 4. Cloning / Updating Repository ==="
TARGET_DIR="$HOME/Provaani_akruti"
if [ -d "$TARGET_DIR" ]; then
  cd "$TARGET_DIR"
  git fetch origin
  git reset --hard origin/main || git reset --hard origin/master
else
  git clone https://github.com/Rahulm043/Provaani_akruti.git "$TARGET_DIR"
  cd "$TARGET_DIR"
fi

echo "=== 5. Setting up .env ==="
if [ ! -f "$TARGET_DIR/.env" ]; then
  cat > "$TARGET_DIR/.env" << 'EOF'
OSS_JWT_SECRET=49f8b417e0e7a177a67f1396b27e8a93cb34de868c26f0bfb557b7fbf1aa5c55
POSTGRES_PASSWORD=postgres
REDIS_PASSWORD=redissecret
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
DEFAULT_ORG_CONCURRENCY_LIMIT=5
FASTAPI_WORKERS=1
ENVIRONMENT=local
EOF
fi

echo "=== 6. Building and Starting Docker Stack ==="
cd "$TARGET_DIR"
sudo docker compose build api custom-ui analysis-service neutts-bridge
sudo docker compose --profile tunnel up -d

echo "=== 7. Waiting for API health ==="
for i in $(seq 1 30); do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/v1/health 2>/dev/null || echo "000")
  echo "Attempt $i: HTTP $STATUS"
  if [ "$STATUS" = "200" ]; then
    echo "API is Healthy!"
    break
  fi
  sleep 5
done

sudo docker ps
echo "=== Bootstrap script complete ==="
