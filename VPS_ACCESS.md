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

## GCP VM Access (Active Deployment)

| Item | Value |
|------|-------|
| VM Name | instance-20260815-072654 |
| Zone | asia-south2-b |
| External IP | 34.131.238.156 |
| GCP Project | project-cb090c10-8c6d-44c8-bbb |
| GCP Account | ashish.kumar.majumder17@gmail.com |
| Custom Dashboard | http://34.131.238.156:3011 or http://34.131.238.156 |
| Admin UI | http://34.131.238.156:3010 |
| Backend API | http://34.131.238.156:8000 |
| Cloudflare Tunnel | https://fully-citysearch-basket-presence.trycloudflare.com |
| Plivo Webhook URL | http://34.131.238.156:8000/api/v1/telephony/plivo-xml |
| Dograh API Key | dgr_tWGgjXa6JoEPEhZ5CtLBZWy5b3-06SzbcmlJu4_bNVI |
| Admin Login | admin@sukanya.com / Admin123! |
| Configured Phone | +918065951924 |

### SSH

```bash
gcloud compute ssh instance-20260815-072654 --zone=asia-south2-b --project=project-cb090c10-8c6d-44c8-bbb
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
