import subprocess

py_code = """
import urllib.request, base64
try:
    req = urllib.request.Request("http://dograhtest-asterisk:8088/ari/applications")
    req.add_header("Authorization", "Basic " + base64.b64encode(b"dograh_app:c9a8b7e6f5d4c3b2a1").decode())
    resp = urllib.request.urlopen(req, timeout=5)
    print("HTTP status:", resp.status)
    print("Body:", resp.read().decode())
except Exception as e:
    print("Error:", e)
"""

cmd = [
    "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
    "-o", "StrictHostKeyChecking=no",
    "rahul@34.131.238.156",
    f"sudo docker exec provaani_akruti-api-1 python -c '{py_code}'"
]

proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
print("stdout:", proc.stdout)
print("stderr:", proc.stderr)
