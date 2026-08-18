import subprocess

sql = "SELECT id, name, workflow_id, mode, state, call_type, is_completed, created_at FROM workflow_runs ORDER BY id DESC LIMIT 15;"
cmd = [
    "gcloud", "compute", "ssh", "instance-20260815-072654",
    "--zone=asia-south2-b",
    "--project=project-cb090c10-8c6d-44c8-bbb",
    f'--command=sudo docker exec provaani_akruti-postgres-1 psql -U postgres -d postgres -c "{sql}"'
]
proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
print("Recent workflow runs:\n", proc.stdout)
