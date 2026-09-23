import subprocess
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ZONE = "asia-south2-b"
PROJECT = "project-cb090c10-8c6d-44c8-bbb"
VM = "instance-20260815-072654"

def run_cmd(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
    return proc.stdout.strip(), proc.stderr.strip(), proc.returncode

def run_ssh(command):
    cmd = ["gcloud", "compute", "ssh", VM, f"--zone={ZONE}", f"--project={PROJECT}", f"--command={command}"]
    return run_cmd(cmd)

print("=== 1. Copying updated files to VM ===")
out, err, code = run_cmd(["gcloud", "compute", "scp", "analysis-service/whatsapp_service.py", f"{VM}:/home/rahul/Provaani_akruti/analysis-service/whatsapp_service.py", f"--zone={ZONE}", f"--project={PROJECT}"])
print("SCP analysis-service/whatsapp_service.py:", "OK" if code == 0 else err)

out, err, code = run_cmd(["gcloud", "compute", "scp", ".env", f"{VM}:/home/rahul/Provaani_akruti/.env", f"--zone={ZONE}", f"--project={PROJECT}"])
print("SCP .env:", "OK" if code == 0 else err)

out, err, code = run_cmd(["gcloud", "compute", "scp", "docker-compose.yaml", f"{VM}:/home/rahul/Provaani_akruti/docker-compose.yaml", f"--zone={ZONE}", f"--project={PROJECT}"])
print("SCP docker-compose.yaml:", "OK" if code == 0 else err)

print("\n=== 2. Updating whatsapp_service.py inside container & restarting ===")
cmd_update = (
    "sudo docker cp /home/rahul/Provaani_akruti/analysis-service/whatsapp_service.py dograhtest-analysis:/app/whatsapp_service.py && "
    "cd /home/rahul/Provaani_akruti && "
    "sudo docker compose up -d --no-deps analysis-service"
)
out, err, code = run_ssh(cmd_update)
print("Update & restart container output:\n", out if code == 0 else err)

time.sleep(3)

print("\n=== 3. Testing /send-whatsapp on dograhtest-analysis:8001 ===")
test_cmd = "sudo docker exec dograhtest-analysis python -c \"import httpx, asyncio, json; r = asyncio.run(httpx.AsyncClient().post('http://127.0.0.1:8001/send-whatsapp', json={'phone_number': '917044311109'})); print('Status:', r.status_code); print('Response:', r.text)\""
cmd = ["gcloud", "compute", "ssh", VM, f"--zone={ZONE}", f"--project={PROJECT}", f"--command={test_cmd}"]
out, err, code = run_cmd(cmd)
print("Endpoint test result:\n", out if code == 0 else err)
