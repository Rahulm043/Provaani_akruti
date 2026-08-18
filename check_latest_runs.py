import subprocess
import json

cmd = [
    "gcloud", "compute", "ssh", "instance-20260815-072654",
    "--zone=asia-south2-b",
    "--project=project-cb090c10-8c6d-44c8-bbb",
    "--command=sudo docker exec provaani_akruti-postgres-1 psql -U postgres -d postgres -c 'SELECT id, workflow_id, state, length(public_access_token) as token_len, public_access_token, created_at FROM workflow_runs ORDER BY id DESC LIMIT 20;'"
]
proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
print("Latest workflow_runs:\n", proc.stdout)
if proc.stderr:
    print("STDERR:", proc.stderr)
