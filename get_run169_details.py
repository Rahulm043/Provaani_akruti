import sys
sys.stdout.reconfigure(encoding='utf-8')
import subprocess
import json

cmd = [
    "gcloud", "compute", "ssh", "instance-20260815-072654",
    "--zone=asia-south2-b",
    "--project=project-cb090c10-8c6d-44c8-bbb",
    "--command=sudo docker exec provaani_akruti-postgres-1 psql -U postgres -d postgres -t -A -c 'SELECT logs FROM workflow_runs WHERE id = 169;'"
]
proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
try:
    data = json.loads(proc.stdout.strip())
    events = data.get("realtime_feedback_events", [])
    print(f"Total events in Run 169: {len(events)}")
    for ev in events:
        ev_type = ev.get("type")
        payload = ev.get("payload", {})
        if ev_type == "rtf-bot-text":
            print(f"BOT: {payload.get('text')}")
        elif ev_type == "rtf-user-transcription" or "user" in ev_type:
            print(f"USER: {payload.get('text')}")
        elif "tool" in ev_type or "function" in ev_type:
            print(f"TOOL: {ev_type} -> {payload}")
except Exception as e:
    print("Error parsing:", e)
    print("Raw stdout snippet:", proc.stdout[:500])
