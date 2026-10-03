import subprocess
import json

cmd = [
    "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
    "-o", "StrictHostKeyChecking=no",
    "rahul@34.131.238.156",
    "sudo docker exec provaani_akruti-postgres-1 psql -U postgres -d postgres -t -c 'SELECT workflow_json FROM workflow_definitions WHERE workflow_id = 3;'"
]
proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
raw = proc.stdout.strip()
data = json.loads(raw)
nodes = data.get("nodes", {})
print("Total nodes:", len(nodes))
print("Node 0 keys:", list(nodes[0].keys()))
print("Node 0 data keys:", list(nodes[0]["data"].keys()))
print("greeting in data:", nodes[0]["data"].get("greeting"))
print("static_greeting in data:", nodes[0]["data"].get("static_greeting"))
print("text in data:", nodes[0]["data"].get("text"))
