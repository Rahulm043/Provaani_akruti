import subprocess

cmd = [
    "gcloud", "compute", "ssh", "instance-20260815-072654",
    "--zone=asia-south2-b",
    "--project=project-cb090c10-8c6d-44c8-bbb",
    '--command=sudo docker exec provaani_akruti-postgres-1 psql -U postgres -d postgres -c "SELECT id, name, created_at, state, is_completed, duration FROM workflow_runs ORDER BY id DESC LIMIT 20;"'
]
proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
print("Latest workflow runs:\n", proc.stdout)
