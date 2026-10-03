import subprocess
import base64

with open(r"c:\Users\rahul\Desktop\Provaani_akruti\scratch\restore_workflow_1.py", "rb") as f:
    content = f.read()

b64_content = base64.b64encode(content).decode("ascii")

remote_script = f"""
echo "{b64_content}" | base64 -d > /tmp/restore_workflow_1.py
sudo docker cp /tmp/restore_workflow_1.py provaani_akruti-api-1:/app/restore_workflow_1.py
sudo docker exec provaani_akruti-api-1 python /app/restore_workflow_1.py
sudo docker exec provaani_akruti-api-1 rm -f /app/restore_workflow_1.py
rm -f /tmp/restore_workflow_1.py
"""

cmd = [
    "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
    "-o", "StrictHostKeyChecking=no",
    "rahul@34.131.238.156",
    remote_script
]

proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
print("stdout:\n", proc.stdout)
print("stderr:\n", proc.stderr)
