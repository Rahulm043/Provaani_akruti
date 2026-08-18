# 🚀 Provaani Production Deployment Guide (New Client / New VM)

This guide provides an end-to-end, reproducible blueprint for provisioning, configuring, hardening, and deploying a **100% production-ready Voice AI Receptionist system** for a new client on a fresh Linux VM.

---

## 🏗️ 1. Architecture & Infrastructure Overview

```
                        ┌────────────────────────────────────────────────────────┐
                        │               GCP VM (2 vCPU / 4 GB RAM)               │
                        │           Static IP: <EXTERNAL_STATIC_IP>              │
                        │                                                        │
Incoming Call           │  ┌───────────────────────┐   ┌──────────────────────┐  │
(Plivo / SIP) ──────────┼─►│ Dograh API (:8000)    │◄──┤ Cerebras (LLM)       │  │
                        │  │ (Pipecat Ingestion)   │──►│ Sarvam AI (TTS)      │  │
                        │  └──────────┬────────────┘   └──────────────────────┘  │
                        │             │                                          │
                        │             ▼                                          │
Client Browser          │  ┌───────────────────────┐   ┌──────────────────────┐  │
https://<subdomain>.    │  │ Custom UI Nginx       │   │ MinIO Object Storage │  │
provaani.xyz ───────────┼─►│ Port 80 & 443 (SSL)   ├──►│ (Recordings & WAVs)  │  │
                        │  └───────────────────────┘   └──────────────────────┘  │
                        │             │                                          │
                        │             ▼                                          │
                        │  ┌───────────────────────┐   ┌──────────────────────┐  │
                        │  │ PostgreSQL 17 (DB)    │   │ Redis 7 (Cache/Queue)│  │
                        │  │ (127.0.0.1:5432)      │   │ (127.0.0.1:6379)     │  │
                        │  └───────────────────────┘   └──────────────────────┘  │
                        └────────────────────────────────────────────────────────┘
```

---

## 📋 2. Cloud & Telephony Prerequisites

### A. Compute Instance (GCP / AWS / Hetzner)
- **OS:** Debian 12 (Bookworm) or Ubuntu 22.04/24.04 LTS
- **Specs:** 2 vCPU, 4 GB RAM, 30 GB SSD
- **Static External IP:** Reserve a permanent static IPv4 address in your cloud console.

### B. Firewall Rules (Ingress Allow)
Configure your cloud firewall (e.g. GCP VPC Firewall) to allow the following ports:
- **`22`** (SSH)
- **`80`** (HTTP - Let's Encrypt & Web Redirect)
- **`443`** (HTTPS - Secure Client Dashboard)
- **`8000`** (Dograh API / Plivo Webhook Ingestion)
- **`3010`** (Dograh Internal Admin Console)
- **`3011`** (Direct Port Fallback for Custom Dashboard)

### C. DNS Configuration (Domain Registrar / Cloudflare)
Add an **A Record** in your DNS management console:
- **Type:** `A`
- **Name / Host:** `<client_name>` (e.g. `akruti` for `akruti.provaani.xyz` or `*` for wildcard multi-tenancy)
- **Target IPv4:** `<EXTERNAL_STATIC_IP>`
- **TTL:** Auto (or 1 min)

---

## 🛠️ 3. VM Initialization & System Setup

Connect to your fresh VM via SSH:

```bash
# 1. Update system packages
sudo apt-get update -y && sudo apt-get upgrade -y

# 2. Install essential dependencies and Certbot
sudo apt-get install -y curl git jq python3 python3-pip certbot

# 3. Install Docker and Docker Compose plugin
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
sudo systemctl enable docker
sudo systemctl start docker

# 4. Configure Docker Daemon Log Rotation (prevents disk exhaustion)
sudo tee /etc/docker/daemon.json << 'EOF'
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "20m",
    "max-file": "3"
  }
}
EOF
sudo systemctl restart docker
```

---

## 🔒 4. SSL Certificate Generation (Let's Encrypt)

Before starting the Docker containers, obtain a standalone SSL certificate for the client's subdomain:

```bash
# Issue certificate (Replace with actual domain and admin email)
sudo certbot certonly --standalone \
  -d <client_subdomain>.provaani.xyz \
  --non-interactive \
  --agree-tos \
  -m admin@provaani.xyz

# Verify certificate was created
sudo ls -la /etc/letsencrypt/live/<client_subdomain>.provaani.xyz/
```

---

## 📦 5. Repository Setup & Environment Configuration

```bash
# 1. Clone the private repository
cd ~
git clone https://github.com/Rahulm043/Provaani_akruti.git
cd ~/Provaani_akruti

# 2. Create the production .env file
cp .env.example .env  # or create from scratch
```

### Populate `.env` with Production Secrets:

```bash
# Generate secure random secrets:
# python3 -c "import secrets; print(secrets.token_hex(24))"

ENVIRONMENT=production
ENABLE_SIGNUP=false

# Core Secrets
OSS_JWT_SECRET="<GENERATE_64_CHAR_HEX>"
POSTGRES_PASSWORD="<GENERATE_48_CHAR_HEX>"
REDIS_PASSWORD="<GENERATE_48_CHAR_HEX>"
MINIO_ROOT_USER="minioadmin"
MINIO_ROOT_PASSWORD="<GENERATE_48_CHAR_HEX>"

# Domain & Networking
PUBLIC_HOST="<EXTERNAL_STATIC_IP>"
PUBLIC_BASE_URL="http://<EXTERNAL_STATIC_IP>:8000"
BACKEND_API_ENDPOINT="http://<EXTERNAL_STATIC_IP>:8000"
MINIO_PUBLIC_ENDPOINT="https://<client_subdomain>.provaani.xyz"

# AI Provider API Keys
CEREBRAS_API_KEY="<CEREBRAS_API_KEY>"
SARVAM_API_KEY="<SARVAM_API_KEY>"
GOOGLE_API_KEY="<GOOGLE_API_KEY>"

# Telephony (Plivo)
PLIVO_AUTH_ID="<PLIVO_AUTH_ID>"
PLIVO_AUTH_TOKEN="<PLIVO_AUTH_TOKEN>"
```

---

## 🚢 6. Deploying & Launching the Docker Stack

```bash
cd ~/Provaani_akruti

# 1. Build Custom UI and analysis services
sudo docker compose build

# 2. Start core services in detached mode
sudo docker compose up -d

# 3. Verify all containers are up and healthy
sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

---

## 👤 7. Creating Admin User & Initializing Workflow

```bash
# 1. Create client admin user via API
curl -X POST "http://127.0.0.1:8000/api/v1/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@provaani.xyz",
    "password": "StrongPassword123!",
    "full_name": "Clinic Administrator",
    "organization_name": "Client Organization"
  }'

# 2. Apply Calibrated Conversational Tuning (500ms Turn Timeout + Language Lock)
python3 apply_language_lock_and_temp.py
```

---

## 📞 8. Telephony Configuration (Plivo Console)

1. Log in to [Plivo Console](https://console.plivo.com/).
2. Navigate to **Voice** ➔ **Applications** ➔ Click on your application (or create a new one).
3. Set the Webhook URLs:
   - **Answer URL:** `http://<EXTERNAL_STATIC_IP>:8000/api/v1/telephony/inbound/run`
   - **Answer URL Method:** `POST`
   - **Hangup URL:** `""` *(LEAVE COMPLETELY EMPTY — DO NOT SET A HANGUP URL)*
   - **Fallback URL:** `""`
4. Attach your Inbound Phone Number to this Application.

---

## ⚙️ 9. Automated Systemd Service, Backups & Maintenance

### A. Auto-Start on Server Reboot (`provaani.service`)
```bash
sudo tee /etc/systemd/system/provaani.service << 'EOF'
[Unit]
Description=Provaani Voice AI Production Stack
After=docker.service network-online.target
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/home/rahul/Provaani_akruti
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable provaani.service
```

### B. Production Logrotate Setup
```bash
sudo cp deploy/provaani-logrotate.conf /etc/logrotate.d/provaani
sudo chmod 644 /etc/logrotate.d/provaani
```

### C. 24/7 Automated Production Cron Jobs
```bash
chmod +x deploy/backup_db.sh deploy/renew_ssl.sh deploy/health_monitor.sh
mkdir -p backups/postgres

(crontab -l 2>/dev/null | grep -v 'warmup_daemon\|cleanup_retention\|backup_db\|renew_ssl\|health_monitor'; cat <<'CRON'
# === Provaani Production Cron Jobs ===
# 24/7 Provider & TLS Warmup Heartbeat (Every 10 minutes)
*/10 * * * * sudo docker exec provaani_akruti-api-1 python3 /app/warmup_daemon.py >> /var/log/provaani_warmup.log 2>&1
# Automated Health Watchdog & Self-Healing (Every 5 minutes)
*/5 * * * * /home/rahul/Provaani_akruti/deploy/health_monitor.sh >> /var/log/provaani_monitor.log 2>&1
# Nightly 3:00 AM Data Retention Cleanup
0 3 * * * sudo docker exec provaani_akruti-api-1 python3 /app/cleanup_retention.py >> /var/log/provaani_cleanup.log 2>&1
# Nightly 2:00 AM PostgreSQL Backup (7-day retention)
0 2 * * * /home/rahul/Provaani_akruti/deploy/backup_db.sh >> /var/log/provaani_backup.log 2>&1
# Weekly Monday 4:00 AM SSL Certificate Renewal
0 4 * * 1 /home/rahul/Provaani_akruti/deploy/renew_ssl.sh >> /var/log/provaani_ssl_renew.log 2>&1
CRON
) | crontab -
```

---

## 🧪 10. Final Production Verification Checklist

Run through this checklist to ensure 100% readiness:

- [ ] **SSL & Web Dashboard:** Visit `https://<client_subdomain>.provaani.xyz` in your browser. Verify the green padlock, Provaani tab title, and logo favicon.
- [ ] **Login:** Sign in with `admin@provaani.xyz` / `StrongPassword123!`.
- [ ] **Inbound Call Test:** Dial the Plivo phone number.
  - [ ] Does the agent answer within 1 second?
  - [ ] Does it detect the caller's language (Bengali / Hindi / English) and stick to it?
  - [ ] Does it tolerate natural 500ms conversational pauses without interrupting?
  - [ ] Does it cleanly execute the `end_call` tool when saying goodbye?
- [ ] **Observability Verification:**
  - [ ] Check `https://<client_subdomain>.provaani.xyz` to confirm the call appeared with correct duration.
  - [ ] Test audio playback of `recordings/<run_id>.wav`.
  - [ ] View transcript modal.
  - [ ] Inspect the Quality Grid (TTFB ~350ms, Latency, Detected Language, Booking intent).
