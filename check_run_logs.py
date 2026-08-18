import subprocess
import json

sql = "SELECT id, state, is_completed, logs FROM workflow_runs WHERE id IN (73, 74);"
cmd = [
    "gcloud", "compute", "ssh", "instance-20260815-072654",
    "--zone=asia-south2-b",
    "--project=project-cb090c10-8c6d-44c8-bbb",
    f'--command=sudo docker exec provaani_akruti-postgres-1 psql -U postgres -d postgres -t -c "{sql}"'
]
proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
print("Logs for 73 & 74:\n", proc.stdout)
