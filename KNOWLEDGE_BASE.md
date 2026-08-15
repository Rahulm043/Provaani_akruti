# Dograh + Sukanya Voice Agent — Knowledge Base

> **Last updated**: 2026-07-06  
> **Status**: Deployed on GCP (Delhi), fully operational  
> **Agent**: Sukanya Classes — Sudipta persona (Bengali/Bonglish counselor)

---

## 1. Deployment (GCP)

| Item | Value |
|------|-------|
| **Provider** | Google Cloud Platform (`mappwithsana@gmail.com`, project `dograh-deployment`) |
| **Region** | `asia-south1-a` (Delhi, India — lowest latency for Indian users) |
| **VM Name** | `dograh-vm` |
| **Machine** | `e2-standard-2` (2 vCPU, 8 GB RAM) — supports up to 5 concurrent Gemini Live calls |
| **Disk** | 30 GB standard persistent disk |
| **External IP** | `35.244.20.132` (ephemeral — may change on stop/start, see below) |
| **SSH zone** | `asia-south1-a` |

### VM Configuration Details

```
Machine type:   e2-standard-2 (2 vCPU shared, 8 GB RAM)
Disk:           30 GB pd-standard (~$1/month storage when stopped)
Region:         asia-south1-a (Delhi, India)
OS:             Ubuntu 22.04 LTS
Docker:         29.6.1
Containers:     7 (api, ui, custom-ui, postgres, redis, minio, cloudflared)
```

### Start / Stop the VM

**TO STOP (end of day — saves credits):**
```bash
gcloud compute instances stop dograh-vm --zone=asia-south1-a
```

**TO START (next day — everything auto-recovers):**
```bash
gcloud compute instances start dograh-vm --zone=asia-south1-a
```

After starting, **wait ~2 minutes** for Docker to boot. Then access the dashboard at `http://<IP>:3011`. 

**IMPORTANT**: The external IP may change after stop/start (it's ephemeral). After starting, check the new IP:
```bash
gcloud compute instances describe dograh-vm --zone=asia-south1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

If the IP changed, update these:
1. The three access URLs below (replace `35.244.20.132` with new IP)
2. The `MINIO_PUBLIC_ENDPOINT` in docker-compose.yaml (line 199)
3. The `BACKEND_URL` in docker-compose.yaml for the UI service
4. Rebuild custom-ui: `cd /root/dograh_test && docker compose build custom-ui && docker compose up custom-ui -d`
5. Restart tunnel: `docker compose restart cloudflared`

Everything else (database, workflows, users, model config, Plivo setup) **persists across restarts** — no reconfiguration needed. Docker starts automatically on boot.

### Access URLs

| Service | URL | Notes |
|---------|-----|-------|
| **Custom Calling Dashboard** | `http://35.244.20.132:3011` | Login, single call, campaigns, call logs |
| **Dograh Admin UI** | `http://35.244.20.132:3010` | Workflow editor, telephony, model config |
| **Dograh API** | `http://35.244.20.132:8000` | REST API |
| **Plivo webhook (tunnel)** | `https://kai-into-mai-emma.trycloudflare.com` | Public URL for Plivo answer_url |

### Login Credentials

| Service | Email | Password |
|---------|-------|----------|
| Dashboard (:3011) | `admin@sukanya.com` | `Admin123!` |
| Admin UI (:3010) | `admin@sukanya.com` | `Admin123!` (requires console workaround, see below) |
| API Key | `dgr_CUpTJkLYCbCYVBTmlpwGn7sWb99hdpcJY1XRS0-NFDI` | Use with `x-api-key` header |

### GCP SSH Commands

```bash
# SSH into VM
gcloud compute ssh dograh-vm --zone=asia-south1-a

# Check running containers
sudo docker ps

# View API logs
sudo docker logs dograh_test-api-1 --tail 50

# Restart everything (if something breaks)
cd /root/dograh_test && sudo docker compose --profile tunnel down && sudo docker compose --profile tunnel up -d

# Rebuild custom-ui after code changes
cd /root/dograh_test && sudo docker compose build custom-ui && sudo docker compose up custom-ui -d

# Rebuild API after patch changes
cd /root/dograh_test && sudo docker compose build api && sudo docker compose up api -d

# Stop VM to save credits
gcloud compute instances stop dograh-vm --zone=asia-south1-a

# Start VM
gcloud compute instances start dograh-vm --zone=asia-south1-a
```

### GCP Billing

- $300 free trial credit on account `mappwithsana@gmail.com`
- `e2-standard-2` costs ~$0.07/hour (~$50/month)
- At $50/month, the $300 credit lasts ~6 months
- **Always stop the VM when not in use** to avoid wasting credits
- When stopped, only the 30 GB disk costs (~$1/month)

---

## 2. Local Development Setup

### Prerequisites

- Windows machine with Docker Desktop installed
- Git
- VPN/SSH key for VPS (if accessing old Provaani VPS)

### Files & Structure

```
C:\Users\rahul\Desktop\Dograh Test\
├── docker-compose.yaml          # Main Docker Compose config
├── Dockerfile.api               # Custom API image (patched Dograh)
├── .env                         # Secrets (JWT, DB passwords, MinIO)
├── .gitignore
├── patches/                     # Dograh API patches
│   └── api/
│       ├── routes/
│       │   └── campaign.py      # Concurrency validation bypass
│       ├── services/
│       │   └── campaign/
│       │       ├── rate_limiter.py           # From-number pool unlock
│       │       └── campaign_call_dispatcher.py  # Rate limit scaling
│       └── db/
│           └── models.py        # (spare copy, not used in patch)
├── custom-ui/                   # React calling dashboard
│   ├── src/
│   │   ├── App.jsx              # Main app + sidebar routing
│   │   ├── components/          # Auth, RecordingPlayer, Skeleton, etc.
│   │   ├── pages/               # Dashboard, SingleCall, CampaignList, etc.
│   │   └── utils/api.js         # API client with authFetch
│   ├── Dockerfile               # Multi-stage build (Node → nginx)
│   ├── nginx-spa.conf           # SPA routing + API proxy
│   └── package.json
└── deploy/
    ├── gcp-deploy.sh            # Full GCP deployment script
    ├── startup.sh               # VM startup script (Docker + compose)
    ├── gcp-setup.sh             # Post-startup telephony/workflow setup
    └── create_key.py            # DB-level API key creation
```

### Start Local Stack

```powershell
# From Dograh Test directory
docker compose build api custom-ui
docker compose --profile tunnel up -d
```

Local endpoints:
- Custom Dashboard: `http://localhost:3011`
- Dograh Admin UI: `http://localhost:3010`
- API: `http://localhost:8000`
- MCP server: `http://localhost:8000/api/v1/mcp/`

---

## 3. Workflow Architecture

### Current Workflow (3-node, merged — deployed on GCP)

```
┌─────────────┐     ┌──────────────────┐     ┌──────────┐
│  GlobalNode │────▶│    StartCall      │────▶│  EndCall │
│  (rules)    │     │ (all conversation)│     │(goodbye) │
└─────────────┘     └──────────────────┘     └──────────┘
```

### Why 3 nodes (not 4)?

**CRITICAL**: The 4-node workflow (startCall → agentNode transition) causes a Gemini Live **disconnect/reconnect** (~956ms pause) every time the agent transitions between nodes. The 3-node version puts ALL conversation content (opening greeting, main conversation, personality, knowledge) in a single `startCall` node. Gemini connects once and stays connected for the entire call. Only transitions to `endCall` when the conversation naturally ends.

### Node Structure

| Node | Type | Role | Key Settings |
|------|------|------|-------------|
| 0 | `globalNode` | Shared rules (ASR handling, formatting, constraints) | Prepended to all nodes with `add_global_prompt: true` |
| 1 | `startCall` | Full conversation + opening + personality | `is_start: true`, `add_global_prompt: true`, `allow_interrupt: true` |
| 3 | `endCall` | Brief warm goodbye | `is_end: true`, `add_global_prompt: false` |

### Prompt Engineering Approach

- **Global Node**: Formatting rules, ASR handling, key constraints (never quote fees, no WhatsApp)
- **Start Call**: Everything — opening greeting ("Namaskar, ami Sudipta bolchhi..."), personality (24-year-old Durgapur counselor, cheerful, uses Bonglish), knowledge (class structure, branches, facilities), call flow (5 phases), tool instructions
- **End Call**: Single instruction — say goodbye naturally in Bengali/Bonglish

### Edge Conditions

| Edge | Condition |
|------|-----------|
| 1→3 (End Call) | "Conversation is naturally over — caller is not interested, has no further questions, time is up, or wrong number." |

### Tools

| Tool | UUID (GCP) | Usage |
|------|------------|-------|
| `transfer_call` | `0857f070-68b8-4e5f-92f5-8dbd5bf3d60a` | Caller asks for senior counselor → transfer to `7044311109` |
| `end_call` | `fa098ae6-dee9-42ef-ae8b-73cb96fcee67` | Created but NOT attached to any node (end call handled by edge transition) |

---

## 4. Model Configuration

| Property | Value |
|----------|-------|
| **Provider** | `google_realtime` (bidirectional streaming) |
| **Model** | `models/gemini-3.1-flash-live-preview` |
| **Voice** | `Aoede` |
| **Language** | `en-US` (personality prompt handles Bonglish switching) |
| **Google API Key** | `REDACTED` |
| **Fallback LLM** | `gemini-2.5-flash-lite` (non-realtime tasks like text analysis) |

### Important Model Notes

- This is a **Live-only** model — it supports only `bidiGenerateContent` (no text generation)
- The `voice` setting still affects output quality even for native audio models
- Use `en-US` language code, not `en` (Gemini WebSocket rejects 2-letter BCP-47 codes with 1011)
- Always prefix model name with `models/` (e.g., `models/gemini-3.1-flash-live-preview`)

### VAD / Turn Detection

The pipeline shows warning: "doesn't emit turn frames". This means server-side VAD (Gemini's built-in voice activity detection) handles turn detection, but doesn't send start/stop boundaries to pipecat. This can cause:
- Slightly delayed responses in the first turn
- Agent waiting too long or not detecting user speech end

The Provaani VPS fix (local VAD via `GeminiVADParams(disabled=True)`) was NOT applied here — it requires deeper pipeline changes.

---

## 5. Telephony (Plivo)

| Property | Value |
|----------|-------|
| **Provider** | Plivo |
| **Config ID** | 1 |
| **Auth ID** | `MANDLJMGQZZGYTNWQ0MY` |
| **Auth Token** | `MTU4NWMyODgtMWJkZC00ZmJlLTUyODEtZWI2NWRi` |
| **Phone Number** | `+918065951924` |
| **Application ID** | Auto-generated by Dograh |
| **answer_url** | `https://kai-into-mai-emma.trycloudflare.com/api/v1/telephony/plivo-xml` |

### Plivo Webhook Flow

1. Dograh initiates call → sends `answer_url` to Plivo
2. Plivo calls the number → when answered, POSTs to `answer_url`
3. `answer_url` must be a **publicly reachable HTTPS URL** → Cloudflare tunnel provides this
4. Tunnel URL changes periodically → restart `cloudflared` if calls fail with "answer_url parameter is not valid"

### Tunnel Restart

```bash
# On the VM
cd /root/dograh_test && sudo docker compose restart cloudflared
# Wait 10 seconds, then check new URL
curl -s http://localhost:8000/api/v1/health | python3 -c 'import json,sys; print(json.load(sys.stdin)["tunnel_url"])'
```

---

## 6. Campaigns & Concurrency

### Patches Applied to Dograh API

We forked the Dograh API to enable **concurrent calls from a single phone number**. Three patches:

| # | File | Change | Why |
|---|------|--------|-----|
| 1 | `patches/api/routes/campaign.py` | `_get_from_numbers_count` returns 100 instead of actual count | Bypasses validation: `max_concurrency ≤ phone_number_count` |
| 2 | `patches/api/services/campaign/rate_limiter.py` | Lua script always returns a number, never marks "in-use" | Allows same Plivo number to be used concurrently |
| 3 | `patches/api/services/campaign/campaign_call_dispatcher.py` | Rate limit scaled by `max_concurrency` | Enables multi-call dispatch (was limited to 1 call/sec) |

### Concurrency Limits

**YES — you can make multiple concurrent calls from the same phone number (`+918065951924`).**

This works because of three patches applied to the Dograh API (see Section 6). Plivo supports concurrent calls from a single number natively. Dograh's built-in restriction (1 call per number) was bypassed.

| Resource | Limit |
|----------|-------|
| Campaign slider (frontend) | 1-5 |
| `DEFAULT_ORG_CONCURRENCY_LIMIT` (.env) | 5 |
| Google Gemini concurrent sessions | Unknown — test before exceeding 5 |
| VM RAM per call | ~300 MB → 5 calls ≈ 1.5 GB (of 8 GB available) |
| Plivo concurrent channels | 5+ (standard accounts) |

**Important caveat**: If you call the **same phone number** multiple times simultaneously, the second call will ring busy because the person is already on the first call. Use **different phone numbers** in your campaign CSV to see true concurrency.

### Rollback Forked API

To revert to the original Dograh API image, change docker-compose.yaml:

```yaml
# Current (forked):
build:
  context: .
  dockerfile: Dockerfile.api
image: dograhtest-custom-api:latest

# Rollback to original:
image: ${REGISTRY:-dograhai}/dograh-api:latest
```

Then `docker compose up api -d`.

---

## 7. API Reference (Key Endpoints)

### Authentication

```bash
# Signup
POST /api/v1/auth/signup  { "email": "...", "password": "...", "name": "..." }

# Login (returns JWT token)
POST /api/v1/auth/login    { "email": "...", "password": "..." }

# Get current user
GET /api/v1/auth/me        Authorization: Bearer <token>

# Create API key (via DB script — no direct API available without key)
docker exec dograh_test-api-1 python3 -c '
import asyncio; from api.db import db_client;
m,k=asyncio.run(db_client.create_api_key(1,"name",1)); print(k)'
```

### Workflows

```bash
# List
GET  /api/v1/workflow/fetch

# Get single
GET  /api/v1/workflow/fetch/{id}

# Create
POST /api/v1/workflow/create/definition   { "name": "...", "workflow_definition": {...} }

# Update
PUT  /api/v1/workflow/{id}                (same body)

# Publish draft
POST /api/v1/workflow/{id}/publish
```

### Calls

```bash
# Initiate single call
POST /api/v1/telephony/initiate-call  { "workflow_id": 1, "phone_number": "+91..." }

# List runs for workflow
GET  /api/v1/workflow/{id}/runs?limit=500

# Get run detail (includes recording URL)
GET  /api/v1/workflow/{wid}/runs/{rid}

# Download recording
GET  /api/v1/public/download/workflow/{token}/recording

# Download transcript
GET  /api/v1/public/download/workflow/{token}/transcript
```

### Campaigns

```bash
# List campaigns
GET    /api/v1/campaign/

# Create campaign (after CSV upload)
POST   /api/v1/campaign/create      { "name": "...", "workflow_id": 1, "max_concurrency": 3, ... }

# Get campaign detail
GET    /api/v1/campaign/{id}

# Controls
POST   /api/v1/campaign/{id}/start
POST   /api/v1/campaign/{id}/pause
POST   /api/v1/campaign/{id}/resume
POST   /api/v1/campaign/{id}/redial

# Campaign runs
GET    /api/v1/campaign/{id}/runs

# Campaign progress
GET    /api/v1/campaign/{id}/progress
```

### Tools

```bash
# List
GET    /api/v1/tools/

# Create
POST   /api/v1/tools/               { "name": "...", "category": "transfer_call", "definition": {...} }
```

### Model Configuration

```bash
# Get
GET    /api/v1/organizations/model-configurations/v2

# Set
PUT    /api/v1/organizations/model-configurations/v2   (requires Bearer token)
```

### Telephony

```bash
# Create config
POST   /api/v1/organizations/telephony-configs

# Add phone number
POST   /api/v1/organizations/telephony-configs/{id}/phone-numbers

# Link phone to workflow
PUT    /api/v1/organizations/telephony-configs/{cid}/phone-numbers/{pid}  { "inbound_workflow_id": 1 }
```

---

## 8. Custom UI Architecture

### Tech Stack

- React 19 + Vite 8 + React Router 7
- SWR for data fetching with auto-refresh
- Lucide React icons
- Provaani dark theme CSS (ported from `provaani-college-demo/frontend`)
- nginx SPA proxy + API reverse proxy

### Pages

| Page | Route | Purpose |
|------|-------|---------|
| Login | `/login` | Dograh auth (email/password → JWT) |
| Dashboard | `/` | Call logs, stats, recording player, transcript |
| Single Call | `/call` | Phone input → initiate Sukanya call |
| Campaigns | `/campaigns` | Campaign list with progress bars |
| New Campaign | `/campaigns/new` | CSV upload OR manual paste, concurrency slider 1-5 |
| Campaign Detail | `/campaigns/:id` | Progress, controls, call records |

### Key Components

| Component | Purpose |
|-----------|---------|
| `AuthProvider.jsx` | JWT auth with Dograh `/api/v1/auth/login` and `/api/v1/auth/me` |
| `RecordingPlayer.jsx` | Audio player with progress, mute, download, track selection |
| `InlineCallDetail.jsx` | Expandable call row with recording, transcript, disposition, telemetry |
| `TranscriptModal.jsx` | Parses Dograh's timestamped transcript format |
| `Skeleton.jsx` | Loading states for stats grid and tables |
| `BackButton.jsx` | Navigation with breadcrumb |

### API Client (`utils/api.js`)

- Uses relative URLs (empty `API_BASE`) → all requests go through nginx proxy
- `authFetch()` attaches `Authorization: Bearer <token>` automatically
- `swrFetcher()` wraps authFetch for SWR hooks
- Token stored in `localStorage` as `dograh_token`
- Auto-redirects to `/login` on 401

### Hardcoded Values (update for new deployments)

| Constant | File | Value | Notes |
|----------|------|-------|-------|
| `WORKFLOW_ID` | `SingleCall.jsx`, `Dashboard.jsx`, `NewCampaign.jsx` | `1` | Update if workflow ID changes |
| `TEL_CONFIG_ID` | `NewCampaign.jsx` | `1` | Telephony config ID |

---

## 9. Admin UI Login Workaround

The Dograh admin UI at `:3010` has a hardcoded `http://localhost:8000` in the login form's JS, which browsers block due to Private Network Access policy. Use this in browser console (F12):

```js
fetch('http://35.244.20.132:8000/api/v1/auth/login', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({email: 'admin@sukanya.com', password: 'Admin123!'})
}).then(r => r.json()).then(d => {
  localStorage.setItem('ACCESS_TOKEN', d.token);
  location.reload();
})
```

After this, the admin UI works normally until the JWT expires.

---

## 10. Troubleshooting

### Call fails with "answer_url parameter is not valid"

**Cause**: Cloudflare tunnel DNS entry expired.  
**Fix**: Restart the tunnel: `docker compose restart cloudflared`

### Campaign concurrency not working

**Cause**: Calls are to the same phone number (person can only take one call at a time).  
**Fix**: Use different phone numbers in the campaign CSV.

### Gemini 1011 error (connection fails)

**Causes & fixes**:
1. Language code is 2-letter (`en`) instead of BCP-47 (`en-US`) → change in model config
2. Model name missing `models/` prefix → use `models/gemini-3.1-flash-live-preview`
3. Google API key rate-limited → wait, or check if Provaani VPS is using the same key
4. Cloudflare tunnel broken → restart tunnel

### Custom-ui container exits with "host not found in upstream"

**Cause**: nginx config references hardcoded container name (`dograhtest-api-1`) instead of Docker service name (`api`).  
**Fix**: In `custom-ui/nginx-spa.conf`, change `proxy_pass http://dograhtest-api-1:8000;` → `proxy_pass http://api:8000;`

### "Workflow not found" when initiating calls

**Cause**: Custom-ui has wrong `WORKFLOW_ID` constant.  
**Fix**: Update `const WORKFLOW_ID = 1;` in `SingleCall.jsx`, `Dashboard.jsx`, `NewCampaign.jsx`. Rebuild custom-ui.

### Dashboard login returns 401

**Cause**: No admin user exists in fresh deployment.  
**Fix**: `POST /api/v1/auth/signup` with email and password.

### API returns "Invalid or expired API key"

**Cause**: API key was generated on a different deployment (different JWT secret).  
**Fix**: Generate new API key on the current deployment via `db_client.create_api_key()`.

---

## 11. Provaani VPS (Reference Only)

The original Provaani system runs on `ubuntu@13.202.209.166` (SSH key: `C:\Users\rahul\Downloads\ai-voice-agent.pem`). **DO NOT MODIFY** — it's read-only for reference.

### Key Differences from Dograh

| Feature | Provaani VPS | Dograh (current) |
|---------|-------------|-----------------|
| Voice output | ElevenLabs "Leda" | Gemini 3.1 native audio "Aoede" |
| VAD | Local VAD (`VADUserTurnStartStrategy`) | Server-side VAD (Gemini default) |
| Telephony API | Custom `server.py` + `telephony_provider.py` | Dograh built-in Plivo integration |
| Agent management | `agents.py` with AgentConfig dataclass | Dograh workflows with nodes/edges |
| Preconnect | `GEMINI_PRECONNECT=true` avoids cold start | No preconnect (cold start = ~500ms) |
| Model ID | `models/gemini-3.1-flash-live-preview` | Same model ID |

---

## 12. Quick Deploy (New GCP Account)

```bash
# 1. Authenticate
gcloud auth login

# 2. Create project & VM
gcloud projects create dograh-deployment
gcloud config set project dograh-deployment
gcloud services enable compute.googleapis.com
gcloud compute firewall-rules create dograh-allow --allow tcp:80,3010,3011,8000,443 --source-ranges=0.0.0.0/0

# 3. Create VM
gcloud compute instances create dograh-vm \
  --zone=asia-south1-a --machine-type=e2-standard-2 --boot-disk-size=30GB \
  --image-family=ubuntu-2204-lts --image-project=ubuntu-os-cloud --tags=dograh-allow \
  --metadata-from-file=startup-script=./deploy/startup.sh

# 4. Get IP
gcloud compute instances describe dograh-vm --zone=asia-south1-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'

# 5. SSH in and run setup
gcloud compute ssh dograh-vm --zone=asia-south1-a
bash /home/rahul/setup.sh   # Upload deploy/gcp-setup.sh first
```

---

## 13. Call Disposition Codes

Automatically assigned by Dograh's pipecat pipeline after each call ends:

| Code | Meaning | When assigned |
|------|---------|---------------|
| `user_qualified` | Caller engaged, showed interest — positive outcome | Conversation naturally ended, agent moved to End Call node |
| `user_hangup` | Caller ended the call voluntarily | Caller pressed end call |
| `user_idle_max_duration_exceeded` | Max call time reached | System timeout |
| `no_answer` | Nobody answered | Plivo reports no pick-up |
| `busy` | Line busy | Plivo reports busy signal |
| `pipeline_error` | Gemini connection failed during call | 1011, network, or API key errors |
