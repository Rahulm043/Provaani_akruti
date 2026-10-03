import subprocess

cmd = [
    "gcloud", "compute", "ssh", "instance-20260815-072654",
    "--zone=asia-south2-b",
    "--project=project-cb090c10-8c6d-44c8-bbb",
    "--command=sudo cat /home/*/.env 2>/dev/null || sudo cat /root/.env 2>/dev/null || sudo docker exec provaani_akruti-api-1 env | grep -E 'GEMINI|GOOGLE|VERCEL|AI_GATEWAY'"
]
proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
print("Output:\n", proc.stdout)
