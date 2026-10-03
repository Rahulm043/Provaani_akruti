import subprocess
import json

cmd = [
    "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
    "-o", "StrictHostKeyChecking=no",
    "rahul@34.131.238.156",
    "sudo docker exec provaani_akruti-postgres-1 psql -U postgres -d postgres -t -A -c 'SELECT workflow_definition FROM workflows WHERE id = 3;'"
]
proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
if proc.returncode != 0:
    print("Error:", proc.stderr)
else:
    data = json.loads(proc.stdout.strip())
    with open("workflow_3_def.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print("Saved workflow_3_def.json! Total nodes:", len(data.get("nodes", [])))
