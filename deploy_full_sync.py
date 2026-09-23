import subprocess
import time
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ZONE = "asia-south2-b"
PROJECT = "project-cb090c10-8c6d-44c8-bbb"
VM = "instance-20260815-072654"

def run_cmd(cmd):
    print(f"CMD: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
    if proc.stdout:
        print(proc.stdout.strip())
    if proc.stderr:
        print("STDERR:", proc.stderr.strip())
    return proc.stdout.strip(), proc.stderr.strip(), proc.returncode

def run_ssh(cmd_str):
    print(f"SSH: {cmd_str}")
    cmd = ["gcloud", "compute", "ssh", VM, f"--zone={ZONE}", f"--project={PROJECT}", f"--command={cmd_str}"]
    return run_cmd(cmd)

def run_scp(local_path, remote_path):
    print(f"SCP: {local_path} -> {remote_path}")
    cmd = ["gcloud", "compute", "scp", "--recurse", local_path, f"{VM}:{remote_path}", f"--zone={ZONE}", f"--project={PROJECT}"]
    return run_cmd(cmd)

print("=== 1. Syncing Files to VM ===")
run_scp(".env", "/home/rahul/Provaani_akruti/.env")
run_scp("docker-compose.yaml", "/home/rahul/Provaani_akruti/docker-compose.yaml")
run_scp("analysis-service", "/home/rahul/Provaani_akruti/")
run_scp("patches", "/home/rahul/Provaani_akruti/")
run_scp("Dockerfile.api", "/home/rahul/Provaani_akruti/Dockerfile.api")

print("\n=== 2. Rebuilding & Updating Analysis Service Container ===")
cmd_analysis = (
    "cd /home/rahul/Provaani_akruti && "
    "sudo docker compose build analysis-service && "
    "sudo docker compose up -d --no-deps analysis-service"
)
run_ssh(cmd_analysis)

print("\n=== 3. Rebuilding & Updating API Container ===")
cmd_api = (
    "cd /home/rahul/Provaani_akruti && "
    "sudo docker build -t dograhtest-custom-api:latest -f Dockerfile.api . && "
    "sudo docker compose up -d --no-deps api"
)
run_ssh(cmd_api)

time.sleep(4)

print("\n=== 4. Re-compiling and Updating Workflow 1 Prompt in DB ===")
update_db_cmd = "sudo docker exec provaani_akruti-api-1 python -c \"import asyncio; from api.db import db_client; from api.routes.campaign import get_active_campaign_settings, compile_unified_prompt; from sqlalchemy import text; async def up(): async with db_client.async_session() as s: res = await s.execute(text('SELECT value FROM organization_settings WHERE organization_id = 1 AND key = \\'campaign_settings\\';')); row = res.first(); import json; d = json.loads(row[0]) if row else {}; prompt = compile_unified_prompt(d); print('Compiled prompt length:', len(prompt)); res2 = await s.execute(text('SELECT definition FROM workflows WHERE id = 1;')); wf_def = json.loads(res2.first()[0]); wf_def['nodes'][0]['data']['prompt'] = prompt; await s.execute(text('UPDATE workflows SET definition = :def WHERE id = 1;'), {'def': json.dumps(wf_def)}); await s.commit(); print('Workflow 1 prompt successfully refreshed in DB!'); asyncio.run(up())\""
run_ssh(update_db_cmd)

print("\n=== 5. Testing WhatsApp Dispatch Endpoint on VM ===")
test_whatsapp_cmd = "sudo docker exec dograhtest-analysis python -c \"import httpx, asyncio; r = asyncio.run(httpx.AsyncClient().post('http://127.0.0.1:8001/send-whatsapp', json={'phone_number': '917044311109'})); print('Status:', r.status_code); print('Response:', r.text)\""
run_ssh(test_whatsapp_cmd)

print("\n=== DEPLOYMENT COMPLETE ===")
