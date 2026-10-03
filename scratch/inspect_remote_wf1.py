import subprocess
import json
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

cmd = [
    "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
    "-o", "StrictHostKeyChecking=no",
    "rahul@34.131.238.156",
    "sudo docker exec provaani_akruti-postgres-1 psql -U postgres -d postgres -t -A -c \"SELECT workflow_configurations FROM workflow_definitions WHERE id = 1;\""
]

proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
cfg = json.loads(proc.stdout.strip())
llm_cfg = cfg['model_configuration_v2_override']['byok']['pipeline']['llm']
stt_cfg = cfg['model_configuration_v2_override']['byok']['pipeline']['stt']
tts_cfg = cfg['model_configuration_v2_override']['byok']['pipeline']['tts']

print("=== WORKFLOW 1 ACTIVE PIPELINE ===")
print("LLM Provider:", llm_cfg.get("provider"))
print("LLM Model:", llm_cfg.get("model"))
print("LLM Base URL:", llm_cfg.get("base_url"))
print("LLM Temp:", llm_cfg.get("temperature"))
print("STT Model:", stt_cfg.get("provider"), stt_cfg.get("model"))
print("TTS Model:", tts_cfg.get("provider"), tts_cfg.get("model"), tts_cfg.get("voice"))
