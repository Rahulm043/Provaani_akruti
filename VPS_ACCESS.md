# Provaani VPS — Access Details
# Last updated: 2026-07-11

## SSH

IP: 13.202.209.166
User: ubuntu
SSH Key: C:\Users\rahul\Downloads\ai-voice-agent.pem

Connect:
```bash
ssh -i "C:\Users\rahul\Downloads\ai-voice-agent.pem" ubuntu@13.202.209.166
```

## Key Files

| File | Purpose |
|------|---------|
| `/home/ubuntu/Provaani-docker/agents.py` | Agent configs (Sukanya, BCREC, etc.) |
| `/home/ubuntu/Provaani-docker/sukanya_new_prompt.json` | Sukanya prompt JSON |
| `/home/ubuntu/Provaani-docker/.env` | Environment (API keys, credentials) |
| `/home/ubuntu/Provaani-docker/server.py` | Plivo webhook server |
| `/home/ubuntu/Provaani-docker/bot_live.py` | Gemini Live bot runtime |
| `/home/ubuntu/Provaani-docker/telephony_provider.py` | Plivo integration |

## Credentials (from .env)

- Google API Key: REDACTED (REVOKED — rotated on 2026-07-06)
- Plivo Auth ID: REPLACED_PLIVO_AUTH_ID
- Plivo Auth Token: REPLACED_PLIVO_AUTH_TOKEN
- Plivo Phone: +918065951924

## GCP VM Access (Provaani Akruti Production Deployment)

| Item | Value |
|------|-------|
| VM Name | instance-20260815-072654 |
| Zone | asia-south2-b (Delhi, India) |
| Machine Type | 2 vCPU, 4 GB RAM |
| External IP | 34.131.238.156 (Permanently Reserved Static IP) |
| Inbound Number | +91 80-31336640 |
| GCP Project | project-cb090c10-8c6d-44c8-bbb |
| Custom Calling Dashboard | http://34.131.238.156:3011 (or http://34.131.238.156) |
| Client Subdomain Target | `akruti.provaani.xyz` (or `*.provaani.xyz`) |
| Dograh Admin UI | http://34.131.238.156:3010 |
| Dograh API | http://34.131.238.156:8000 |
| API Health | http://34.131.238.156:8000/api/v1/health |
| Login Credentials | `admin@provaani.xyz` / `Admin123!` (Org ID: 1) |
| Database Security | PostgreSQL & Redis bound to `127.0.0.1` (localhost only) |
| Cloudflare Tunnel | DISABLED (Direct Public Static IP Webhooks) |

### 🌐 Custom Domain Setup (`provaani.xyz`)

To point `akruti.provaani.xyz` (and any future client subdomains) to this dashboard:

1. **Add DNS A Record in your DNS Provider (e.g. Cloudflare DNS / Namecheap / GoDaddy):**
   - **Type:** `A`
   - **Name:** `akruti` (or `*.provaani.xyz` for wildcard all clients)
   - **IPv4 Address:** `34.131.238.156`
   - **Proxy Status:** Proxied (Cloudflare Orange Cloud for instant free HTTPS) or DNS only
   - **TTL:** Auto / 1 min

2. **Nginx Routing:**
   - The Nginx server on the VM is configured with `server_name _ localhost *.provaani.xyz akruti.provaani.xyz provaani.xyz;` on ports 80 and 3011.
   - Any subdomain traffic pointing to `34.131.238.156` immediately serves the custom calling dashboard.

### SSH

Prerequisites: Google Cloud SDK installed (gcloud CLI).

```bash
# From your terminal (PowerShell/CMD):
gcloud auth login  # Opens browser — log in as mappwithsana@gmail.com

# SSH into VM
gcloud compute ssh dograh-vm --zone=asia-south1-a
```

### Manage the VM

```bash
# Start
gcloud compute instances start dograh-vm --zone=asia-south1-a

# Stop (saves credits)
gcloud compute instances stop dograh-vm --zone=asia-south1-a

# Get current IP
gcloud compute instances describe dograh-vm --zone=asia-south1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

### Inside the VM (after SSH)

```bash
# Check containers
sudo docker ps

# View API logs
sudo docker logs dograh_test-api-1 --tail 50

# Rebuild custom UI after code changes
cd /root/dograh_test && sudo docker compose build custom-ui && sudo docker compose up custom-ui -d

# Restart the whole stack
cd /root/dograh_test && sudo docker compose --profile tunnel down && sudo docker compose --profile tunnel up -d
```

## Notes

- This VPS is READ-ONLY — do not modify files
- The old Google API key was exposed and REVOKED
- New key is REDACTED
