import subprocess
import base64
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

with open(r"c:\Users\rahul\Desktop\Provaani_akruti\scratch\apply_openrouter_gpt4o_mini.py", "rb") as f:
    content = f.read()

b64_content = base64.b64encode(content).decode("ascii")

remote_script = f"""
echo "{b64_content}" | base64 -d > /tmp/apply_openrouter_gpt4o_mini.py
sudo docker cp /tmp/apply_openrouter_gpt4o_mini.py provaani_akruti-api-1:/app/apply_openrouter_gpt4o_mini.py
sudo docker exec provaani_akruti-api-1 python /app/apply_openrouter_gpt4o_mini.py
sudo docker exec provaani_akruti-api-1 rm -f /app/apply_openrouter_gpt4o_mini.py
rm -f /tmp/apply_openrouter_gpt4o_mini.py
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
