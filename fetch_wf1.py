import subprocess
import json

cmd = [
    "gcloud", "compute", "ssh", "instance-20260815-072654",
    "--zone=asia-south2-b",
    "--project=project-cb090c10-8c6d-44c8-bbb",
    "--command=sudo docker exec provaani_akruti-postgres-1 psql -U postgres -d postgres -t -A -c \"SELECT json_build_object('workflow', row_to_json(w), 'definition', row_to_json(wd)) FROM workflows w JOIN workflow_definitions wd ON w.id = wd.workflow_id WHERE w.id = 1;\""
]
proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
if proc.stdout:
    with open("c:/Users/rahul/Desktop/Provaani_akruti/wf1_dump.json", "w", encoding="utf-8") as f:
        f.write(proc.stdout)
    print("Dumped wf1 successfully, length:", len(proc.stdout))
else:
    print("Stdout empty. Stderr:", proc.stderr)
