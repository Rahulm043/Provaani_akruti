import subprocess

sql = """
SELECT id, name, mode, state, is_completed, created_at,
       logs->'inbound_webhook'->'raw_webhook_data'->>'CallUUID' as call_uuid,
       logs->'inbound_webhook'->'raw_webhook_data'->>'Event' as event
FROM workflow_runs
WHERE state = 'initialized' AND is_completed = false;
"""
cmd = [
    "gcloud", "compute", "ssh", "instance-20260815-072654",
    "--zone=asia-south2-b",
    "--project=project-cb090c10-8c6d-44c8-bbb",
    "--command=sudo docker exec provaani_akruti-postgres-1 psql -U postgres -d postgres -c \"SELECT id, name, mode, state, is_completed, created_at FROM workflow_runs WHERE is_completed = false;\""
]
proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
print("Orphaned initialized runs:\n", proc.stdout)
