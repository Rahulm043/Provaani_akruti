import time
import subprocess
import json
import urllib.request
import urllib.error

VM_IP = "34.131.238.156"
ZONE = "asia-south2-b"
PROJECT = "project-cb090c10-8c6d-44c8-bbb"
VM_NAME = "instance-20260815-072654"

def run_ssh(cmd):
    full_cmd = f'gcloud compute ssh {VM_NAME} --zone={ZONE} --project={PROJECT} --command="{cmd}"'
    res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr

print(f"=== Starting auto deployment monitor for {VM_IP} ===", flush=True)

# Step 1: Wait for API to be healthy
for i in range(120): # up to 10 minutes
    try:
        req = urllib.request.Request(f"http://{VM_IP}:8000/api/v1/health")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                print(f"[SUCCESS] API is healthy at http://{VM_IP}:8000/api/v1/health!", flush=True)
                break
    except Exception:
        pass
    
    # Check docker status on VM every 15s
    if i % 3 == 0:
        ret, out, err = run_ssh("sudo docker ps --format '{{.Names}} {{.Status}}'")
        print(f"[{i*5}s] Containers: {out.strip() if out.strip() else 'building/starting...'}", flush=True)
    
    time.sleep(5)

print("=== Running Post-Deployment Configuration Script on VM ===", flush=True)

# Upload setup script to VM
setup_script = r'''#!/bin/bash
set -e

echo "=== 1. Creating Admin User ==="
curl -s -X POST http://localhost:8000/api/v1/auth/signup \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@sukanya.com","password":"Admin123!","name":"Admin"}' | python3 -c 'import json,sys; d=json.load(sys.stdin); print("Signup:", d.get("detail","OK"))'

echo "=== 2. Creating API Key ==="
API_CONTAINER=$(sudo docker ps --filter "name=api" --format "{{.Names}}" | head -n 1)
echo "API Container: $API_CONTAINER"
APIKEY=$(sudo docker exec "$API_CONTAINER" python3 -c 'import asyncio; from api.db import db_client; m,k=asyncio.run(db_client.create_api_key(1,"cli",1)); print(k)')
echo "API Key: $APIKEY"

echo "=== 3. Getting Auth Token ==="
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@sukanya.com","password":"Admin123!"}' | python3 -c 'import json,sys; print(json.load(sys.stdin).get("token","FAILED"))')
echo "Token obtained."

echo "=== 4. Setting Model Configuration ==="
curl -s -X PUT http://localhost:8000/api/v1/organizations/model-configurations/v2 \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"version":2,"mode":"byok","byok":{"mode":"realtime","realtime":{"realtime":{"provider":"google_realtime","api_key":["REPLACED_GCP_API_KEY"],"model":"models/gemini-3.1-flash-live-preview","voice":"Aoede","language":"en-US"},"llm":{"provider":"google","api_key":["REPLACED_GCP_API_KEY"],"model":"gemini-2.5-flash-lite"}}}}' | python3 -c 'import json,sys; d=json.load(sys.stdin); print("Model configured:", d.get("configuration",{}).get("realtime",{}).get("model",d.get("detail","OK")))'

echo "=== 5. Setting up Plivo Telephony ==="
PLIVO_RES=$(curl -s -X POST http://localhost:8000/api/v1/organizations/telephony-configs \
  -H "x-api-key: $APIKEY" -H 'Content-Type: application/json' \
  -d '{"provider":"plivo","name":"Plivo - Provaani","credentials":{"auth_id":"REPLACED_PLIVO_AUTH_ID","auth_token":"REPLACED_PLIVO_AUTH_TOKEN"},"config":{"provider":"plivo","auth_id":"REPLACED_PLIVO_AUTH_ID","auth_token":"REPLACED_PLIVO_AUTH_TOKEN"}}')
echo "Plivo Response: $PLIVO_RES"

echo "=== 6. Adding Phone Number ==="
PHONE_RES=$(curl -s -X POST http://localhost:8000/api/v1/organizations/telephony-configs/1/phone-numbers \
  -H "x-api-key: $APIKEY" -H 'Content-Type: application/json' \
  -d '{"address":"+918065951924","nickname":"Sukanya","is_default_caller_id":true}')
echo "Phone Response: $PHONE_RES"

echo "=== 7. Creating Tools ==="
TRANSFER=$(curl -s -X POST http://localhost:8000/api/v1/tools/ \
  -H "x-api-key: $APIKEY" -H 'Content-Type: application/json' \
  -d '{"name":"transfer_call","description":"Transfer to senior counselor","category":"transfer_call","definition":{"type":"transfer_call","config":{"destination":"7044311109"}}}' | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_uuid","FAIL"))')
echo "Transfer Tool UUID: $TRANSFER"

ENDU=$(curl -s -X POST http://localhost:8000/api/v1/tools/ \
  -H "x-api-key: $APIKEY" -H 'Content-Type: application/json' \
  -d '{"name":"end_call","description":"End call","category":"end_call","definition":{"type":"end_call","config":{}}}' | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_uuid","FAIL"))')
echo "EndCall Tool UUID: $ENDU"

echo "=== 8. Creating & Publishing Workflow ==="
python3 -c "
import json
wf = {
    'name': 'sukanya - outbound',
    'workflow_definition': {
        'nodes': [
            {
                'id': '0', 'type': 'globalNode',
                'position': {'x': -325, 'y': 480},
                'data': {
                    'name': 'Global Node',
                    'prompt': '## FORMATTING RULES\n- Keep responses short: 1-3 sentences. Never monologue.\n- Use natural Bonglish. Use fillers naturally: accha, mane, bujhlam, thikache.\n- No markdown, no bullets, no formatting. Spoken output only.\n- Never use: Certainly, Absolutely, I would be happy to help, Great question.\n\n## HANDLING ASR ISSUES\n- If the callers message looks garbled, make a reasonable guess and continue.\n- Only ask for clarification if critical.\n\n## KEY RULES\n- Never repeat a question the caller already answered.\n- Never quote exact fees. Say a senior counselor will discuss.\n- Never criticize other coaching institutes.\n- Do NOT promise WhatsApp or emails.\n- If interested, offer: callback or branch visit. Share: 8637583173, 9002005526, sukanyaclasses.com',
                    'allow_interrupt': False, 'invalid': False, 'validationMessage': None, 'is_static': False
                },
                'measured': {'width': 320, 'height': 128}
            },
            {
                'id': '1', 'type': 'startCall',
                'position': {'x': 175, 'y': 60},
                'data': {
                    'name': 'Start Call',
                    'prompt': 'Namaskar, ami Sudipta bolchhi. Sukanya Classes, Durgapur theke calling korchhi. Aapni ki ektu kotha bolte parben?\n\nOnce they say yes, tell them briefly about Sukanya Classes and why you are calling. Keep it to 2-3 sentences. Ask if they have a school-going child.\n\nMove to Main Conversation after they engage.',
                    'allow_interrupt': False, 'invalid': False, 'validationMessage': None, 'is_static': False,
                    'add_global_prompt': True, 'wait_for_user_response': False, 'detect_voicemail': False,
                    'delayed_start': False, 'is_start': True, 'selected_through_edge': False, 'hovered_through_edge': False
                },
                'measured': {'width': 320, 'height': 128}
            },
            {
                'id': '2', 'type': 'agentNode',
                'position': {'x': 615.5, 'y': 476},
                'data': {
                    'name': 'Main Conversation',
                    'prompt': '## Personality\n\nSudipta is twenty-four, from Durgapur, working at Sukanya Classes. Cheerful and relaxed. Speaks Bonglish naturally — Bengali and English folding into each other. Uses fillers: accha, mane, bujhlam, thik ache. Slides into Hindi or English easily. Uses feminine grammatical forms.\n\n## Knowledge\n\nSukanya Classes: runs daily 4-9 PM, Class 1-12, CBSE and ICSE. Small batches (max 10). Audio-visual classrooms, science labs, CCTV, transport. Branches: Phuljhore, Benachity, Raniganj.\n\n## Task\n\nCalling parents in and around Durgapur. Open naturally. Explain Sukanya briefly. Ask if they have a school-going child. Let the conversation flow naturally.\n\n## Call Arc\nPhase 1: Short first turn - name, org, check if good time.\nPhase 2: Briefly explain Sukanya — small batches, labs, AV teaching. Ask about school-going child.\nPhase 3: Explore their childs class, subjects, struggles. Ask natural follow-ups. Listen more than talk.\nPhase 4: Connect one relevant Sukanya benefit. Let them react.\nPhase 5: Close naturally. If interested, offer callback or branch visit.\n\n## Tools\n- transfer_call: Use when caller explicitly asks for a senior counselor. Say a short handoff sentence first.\n\nContact: 8637583173, 9002005526, sukanyaclasses.com',
                    'allow_interrupt': True, 'invalid': False, 'validationMessage': None,
                    'extraction_enabled': False, 'extraction_prompt': '', 'extraction_variables': [],
                    'add_global_prompt': True, 'tool_uuids': ['$TRANSFER'],
                    'selected_through_edge': False, 'hovered_through_edge': False
                },
                'measured': {'width': 320, 'height': 128}
            },
            {
                'id': '3', 'type': 'endCall',
                'position': {'x': 175, 'y': 900},
                'data': {
                    'name': 'End Call',
                    'prompt': 'The conversation is complete. Say a brief warm goodbye naturally in Bengali/Bonglish. Do not ask follow-up questions.',
                    'allow_interrupt': False, 'invalid': False, 'validationMessage': None, 'is_static': False,
                    'extraction_enabled': False, 'extraction_prompt': '', 'extraction_variables': [],
                    'add_global_prompt': False, 'is_end': True, 'selected_through_edge': False, 'hovered_through_edge': False
                },
                'measured': {'width': 320, 'height': 128}
            }
        ],
        'edges': [
            {
                'id': '1-2', 'animated': True, 'type': 'custom', 'source': '1', 'target': '2',
                'data': {'condition': 'Caller is free to talk and you have introduced yourself.', 'label': 'Main Conversation', 'invalid': False, 'validationMessage': None}
            },
            {
                'id': '1-3', 'animated': True, 'type': 'custom', 'source': '1', 'target': '3',
                'data': {'condition': 'Wrong number, not interested, or busy.', 'label': 'End Call', 'invalid': False, 'validationMessage': None}
            },
            {
                'id': '2-3', 'animated': True, 'type': 'custom', 'source': '2', 'target': '3',
                'data': {'condition': 'Conversation is naturally over.', 'label': 'End Call', 'invalid': False, 'validationMessage': None}
            }
        ]
    }
}
print(json.dumps(wf))
" > /tmp/wf.json

curl -s -X POST http://localhost:8000/api/v1/workflow/create/definition \
  -H "x-api-key: $APIKEY" -H 'Content-Type: application/json' \
  -d @/tmp/wf.json | python3 -c 'import json,sys; print("WF Created ID:", json.load(sys.stdin).get("id","FAILED"))'

curl -s -X POST http://localhost:8000/api/v1/workflow/1/publish -H "x-api-key: $APIKEY" | python3 -c 'import json,sys; print("WF Published:", json.load(sys.stdin).get("status","FAILED"))'

echo "=== 9. Linking Phone Number to Workflow ==="
curl -s -X PUT http://localhost:8000/api/v1/organizations/telephony-configs/1/phone-numbers/1 \
  -H "x-api-key: $APIKEY" -H 'Content-Type: application/json' \
  -d '{"inbound_workflow_id":1}' | python3 -c 'import json,sys; print("Phone Linked:", json.load(sys.stdin).get("detail","OK"))'

echo "=== DEPLOYMENT AND CONFIGURATION FULLY COMPLETED ==="
'''

with open("gcp_post_setup.sh", "w") as f:
    f.write(setup_script)

subprocess.run(f"gcloud compute scp gcp_post_setup.sh {VM_NAME}:~/gcp_post_setup.sh --zone={ZONE} --project={PROJECT}", shell=True)
ret, out, err = run_ssh("chmod +x ~/gcp_post_setup.sh && ~/gcp_post_setup.sh")
print(out, flush=True)
if err:
    print("Errors:", err, flush=True)

print("=== VERIFYING ACCESSIBILITY OF ALL SERVICES ===", flush=True)
endpoints = [
    ("API Health", f"http://{VM_IP}:8000/api/v1/health"),
    ("Custom UI (Dashboard)", f"http://{VM_IP}:3011"),
    ("Custom UI (Port 80)", f"http://{VM_IP}:80"),
    ("Admin UI", f"http://{VM_IP}:3010")
]

for name, url in endpoints:
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as r:
            print(f"[OK] {name}: {url} -> Status {r.status}", flush=True)
    except Exception as e:
        print(f"[FAILED] {name}: {url} -> {e}", flush=True)

print("=== ALL DONE! ===", flush=True)
