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

print("=== 1. Copying updated whatsapp_service.py to VM and restarting analysis container ===")
out, err, code = run_cmd(["gcloud", "compute", "scp", "analysis-service/whatsapp_service.py", f"{VM}:/home/rahul/Provaani_akruti/analysis-service/whatsapp_service.py", f"--zone={ZONE}", f"--project={PROJECT}"])
print("SCP whatsapp_service.py:", "OK" if code == 0 else err)

cmd_restart_analysis = (
    "cd /home/rahul/Provaani_akruti && "
    "sudo docker compose restart analysis"
)
out, err, code = run_ssh(cmd_restart_analysis)
print("Restart analysis container:", out if code == 0 else err)

time.sleep(3)

print("\n=== 2. Testing /send-whatsapp on dograhtest-analysis:8001 ===")
test_cmd = (
    "sudo docker exec dograhtest-analysis python -c \""
    "import asyncio, httpx; "
    "async def t(): "
    "    async with httpx.AsyncClient() as c: "
    "        r = await c.post('http://127.0.0.1:8001/send-whatsapp', json={'phone_number': '+917044311109', 'caller_name': 'Rahul', 'procedure_of_interest': 'Liposuction'}); "
    "        print('Test endpoint status:', r.status_code, r.text); "
    "asyncio.run(t())\""
)
out, err, code = run_ssh(test_cmd)
print("Endpoint test result:\n", out if code == 0 else err)

print("\n=== 3. Updating Workflow 1 Prompt & Conversational Rules in PostgreSQL ===")
run_cmd(["gcloud", "compute", "scp", "update_spelling_and_repetition.py", f"{VM}:/home/rahul/Provaani_akruti/update_spelling_and_repetition.py", f"--zone={ZONE}", f"--project={PROJECT}"])

cmd_exec_prompt = (
    "sudo docker cp /home/rahul/Provaani_akruti/update_spelling_and_repetition.py provaani_akruti-api-1:/app/update_spelling_and_repetition.py && "
    "sudo docker exec provaani_akruti-api-1 python /app/update_spelling_and_repetition.py && "
    "sudo docker exec provaani_akruti-api-1 rm -f /app/update_spelling_and_repetition.py && "
    "rm -f /home/rahul/Provaani_akruti/update_spelling_and_repetition.py"
)
out, err, code = run_ssh(cmd_exec_prompt)
print("Prompt update result:\n", out if code == 0 else err)
