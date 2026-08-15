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
- Plivo Auth ID: MANDLJMGQZZGYTNWQ0MY
- Plivo Auth Token: MTU4NWMyODgtMWJkZC00ZmJlLTUyODEtZWI2NWRi
- Plivo Phone: +918065951924

## GCP VM Access (current active deployment)

| Item | Value |
|------|-------|
| VM Name | dograh-vm |
| Zone | asia-south1-a |
| External IP | 8.231.88.232 (ephemeral — may change on stop/start) |
| GCP Project | dograh-deployment |
| GCP Account | mappwithsana@gmail.com |
| Custom Dashboard | http://8.231.88.232:3011 |
| Admin UI | http://8.231.88.232:3010 |
| Dograh API Key | dgr_CUpTJkLYCbCYVBTmlpwGn7sWb99hdpcJY1XRS0-NFDI |
| Login | admin@sukanya.com / Admin123! |

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
