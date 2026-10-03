import subprocess

cmd = [
    "gcloud", "compute", "ssh", "instance-20260815-072654",
    "--zone=asia-south2-b",
    "--project=project-cb090c10-8c6d-44c8-bbb",
    "--command=sudo docker exec provaani_akruti-api-1 python -c \"with open('/opt/venv/lib/python3.13/site-packages/pipecat/services/google/gemini_live/llm.py') as f: lines = f.readlines(); print(''.join(lines[350:500]))\""
]
proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
with open("c:/Users/rahul/Desktop/Provaani_akruti/gemini_live_connect.py", "w", encoding="utf-8") as out:
    out.write(proc.stdout)
print("Wrote snippet length:", len(proc.stdout))
