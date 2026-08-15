#!/bin/bash
# Setup Dograh on GCP
set -e

echo "=== Creating admin user ==="
curl -s -X POST http://localhost:8000/api/v1/auth/signup \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@sukanya.com","password":"Admin123!","name":"Admin"}' | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d.get("detail","OK"))'

echo "=== Creating API key ==="
APIKEY=$(sudo docker exec dograh_test-api-1 python3 -c 'import asyncio; from api.db import db_client; m,k=asyncio.run(db_client.create_api_key(1,"cli",1)); print(k)')
echo "APIKEY=$APIKEY"

echo "=== Setting model config ==="
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"admin@sukanya.com","password":"Admin123!"}' | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')
curl -s -X PUT http://localhost:8000/api/v1/organizations/model-configurations/v2 \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"version":2,"mode":"byok","byok":{"mode":"realtime","realtime":{"realtime":{"provider":"google_realtime","api_key":["REDACTED"],"model":"models/gemini-3.1-flash-live-preview","voice":"Aoede","language":"en-US"},"llm":{"provider":"google","api_key":["REDACTED"],"model":"gemini-2.5-flash-lite"}}}}' | python3 -c 'import json,sys; d=json.load(sys.stdin); print("Model:", d.get("configuration",{}).get("realtime",{}).get("model",d.get("detail","?")))'

echo "=== Creating Plivo config ==="
curl -s -X POST http://localhost:8000/api/v1/organizations/telephony-configs \
  -H "x-api-key: $APIKEY" -H 'Content-Type: application/json' \
  -d '{"provider":"plivo","name":"Plivo - Provaani","credentials":{"auth_id":"REPLACED_PLIVO_AUTH_ID","auth_token":"REDACTED"},"config":{"provider":"plivo","auth_id":"REPLACED_PLIVO_AUTH_ID","auth_token":"REDACTED"}}' | python3 -c 'import json,sys; print("Plivo ID:", json.load(sys.stdin).get("id","FAILED"))'

echo "=== Adding phone number ==="
curl -s -X POST http://localhost:8000/api/v1/organizations/telephony-configs/1/phone-numbers \
  -H "x-api-key: $APIKEY" -H 'Content-Type: application/json' \
  -d '{"address":"+918065951924","nickname":"Sukanya","is_default_caller_id":true}' | python3 -c 'import json,sys; print("Phone ID:", json.load(sys.stdin).get("id","FAILED"))'

echo "=== Creating tools ==="
TRANSFER=$(curl -s -X POST http://localhost:8000/api/v1/tools/ \
  -H "x-api-key: $APIKEY" -H 'Content-Type: application/json' \
  -d '{"name":"transfer_call","description":"Transfer to senior counselor","category":"transfer_call","definition":{"type":"transfer_call","config":{"destination":"7044311109"}}}' | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_uuid","FAIL"))')
echo "Transfer UUID: $TRANSFER"

ENDU=$(curl -s -X POST http://localhost:8000/api/v1/tools/ \
  -H "x-api-key: $APIKEY" -H 'Content-Type: application/json' \
  -d '{"name":"end_call","description":"End call","category":"end_call","definition":{"type":"end_call","config":{}}}' | python3 -c 'import json,sys; print(json.load(sys.stdin).get("tool_uuid","FAIL"))')
echo "EndCall UUID: $ENDU"

echo "=== Creating workflow ==="
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
  -d @/tmp/wf.json | python3 -c 'import json,sys; print("WF ID:", json.load(sys.stdin).get("id","FAILED"))'

curl -s -X POST http://localhost:8000/api/v1/workflow/1/publish -H "x-api-key: $APIKEY" | python3 -c 'import json,sys; print("Published:", json.load(sys.stdin).get("status","FAILED"))'

echo "=== Linking phone to workflow ==="
curl -s -X PUT http://localhost:8000/api/v1/organizations/telephony-configs/1/phone-numbers/1 \
  -H "x-api-key: $APIKEY" -H 'Content-Type: application/json' \
  -d '{"inbound_workflow_id":1}' | python3 -c 'import json,sys; print("Linked:", json.load(sys.stdin).get("detail","OK"))'

echo ""
echo "=== SETUP COMPLETE ==="
echo "IP: 35.244.20.132"
echo "Login: admin@sukanya.com / Admin123!"
echo "API Key: $APIKEY"
echo "Custom UI: http://35.244.20.132:3011"
echo "Admin UI: http://35.244.20.132:3010"