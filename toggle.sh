#!/bin/bash
# Toggle between Realtime (Gemini Live) and Cascaded (Smallest + Cerebras) pipelines
# Usage: bash toggle.sh [realtime|cascaded]

APIKEY='REPLACED_DOGRAH_API_KEY'
DOGRAH_API='http://localhost:8000'
TARGET="${1:-status}"

if [ "$TARGET" = "realtime" ]; then
  echo "=== Switching to Realtime pipeline (Gemini Live) ==="
  curl -s -X PUT "$DOGRAH_API/api/v1/organizations/model-configurations/v2" \
    -H "x-api-key: $APIKEY" -H 'Content-Type: application/json' \
    -d @/tmp/realtime_backup.json | python3 -c 'import json,sys; d=json.load(sys.stdin); c=d.get("effective_configuration",{}); print("Mode:", "Realtime" if c.get("is_realtime") else "Pipeline"); print("LLM:", c.get("realtime",{}).get("model","N/A")); print("TTS:", "Gemini Live")'

elif [ "$TARGET" = "cascaded" ]; then
  echo "=== Switching to Cascaded pipeline (Smallest STT + Cerebras LLM + Smallest TTS) ==="
  curl -s -X PUT "$DOGRAH_API/api/v1/organizations/model-configurations/v2" \
    -H "x-api-key: $APIKEY" -H 'Content-Type: application/json' \
    -d @/tmp/cc.json | python3 -c 'import json,sys; d=json.load(sys.stdin); c=d.get("effective_configuration",{}); print("Mode:", "Cascaded" if not c.get("is_realtime") else "?"); print("STT:", c.get("stt",{}).get("provider","N/A")); print("LLM:", c.get("llm",{}).get("provider","N/A"), c.get("llm",{}).get("model","N/A")); print("TTS:", c.get("tts",{}).get("provider","N/A"), c.get("tts",{}).get("voice","N/A"))'

elif [ "$TARGET" = "status" ]; then
  echo "=== Current Pipeline Status ==="
  curl -s "$DOGRAH_API/api/v1/organizations/model-configurations/v2" \
    -H "x-api-key: $APIKEY" | python3 -c 'import json,sys; d=json.load(sys.stdin); c=d.get("effective_configuration",{}); print("Is Realtime:", c.get("is_realtime")); print("Mode:", c.get("mode","?")); [print(k.upper()+":", v.get("provider","N/A")) for k,v in c.items() if isinstance(v,dict) and "provider" in v]'

else
  echo "Usage: bash toggle.sh [realtime|cascaded|status]"
fi
