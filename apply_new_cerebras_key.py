import subprocess
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

ZONE = "asia-south2-b"
PROJECT = "project-cb090c10-8c6d-44c8-bbb"
VM = "instance-20260815-072654"
import os
NEW_KEY = os.environ.get("CEREBRAS_API_KEY", "")

def run_cmd(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
    return proc.stdout.strip(), proc.stderr.strip(), proc.returncode

def run_ssh(command):
    cmd = ["gcloud", "compute", "ssh", VM, f"--zone={ZONE}", f"--project={PROJECT}", f"--command={command}"]
    return run_cmd(cmd)

print("=== 1. Copying updated .env to VM ===")
out, err, code = run_cmd(["gcloud", "compute", "scp", ".env", f"{VM}:/home/rahul/Provaani_akruti/.env", f"--zone={ZONE}", f"--project={PROJECT}"])
print("SCP .env:", "OK" if code == 0 else err)

print("\n=== 2. Updating Cerebras API key in PostgreSQL database ===")
update_db_script = f"""
import asyncio
from api.db import db_client
from sqlalchemy import text
import json

async def main():
    async with db_client.async_session() as session:
        # Update published workflow definitions
        res = await session.execute(text("SELECT id, configurations FROM workflow_definitions WHERE workflow_id = 1;"))
        rows = res.fetchall()
        for r in rows:
            def_id = r[0]
            config = r[1]
            if isinstance(config, str):
                config = json.loads(config)
            
            # Update key in pipeline
            try:
                config['model_configuration_v2_override']['byok']['pipeline']['llm']['api_key'] = ['{NEW_KEY}']
                await session.execute(
                    text("UPDATE workflow_definitions SET configurations = :cfg WHERE id = :id;"),
                    {{"cfg": json.dumps(config), "id": def_id}}
                )
                print(f"Updated workflow_definition ID {{def_id}} with new Cerebras key.")
            except Exception as e:
                print(f"Error updating def {{def_id}}: {{e}}")
                
        await session.commit()
        print("Database update committed successfully.")

asyncio.run(main())
"""

# Write update script to VM and execute inside API container
cmd_write_script = f"cat << 'EOF' > /home/rahul/Provaani_akruti/update_key_temp.py\n{update_db_script}\nEOF"
run_ssh(cmd_write_script)

cmd_run_db = (
    "sudo docker cp /home/rahul/Provaani_akruti/update_key_temp.py provaani_akruti-api-1:/app/update_key_temp.py && "
    "sudo docker exec provaani_akruti-api-1 python /app/update_key_temp.py && "
    "sudo docker exec provaani_akruti-api-1 rm -f /app/update_key_temp.py && "
    "rm -f /home/rahul/Provaani_akruti/update_key_temp.py"
)
out, err, code = run_ssh(cmd_run_db)
print("DB Update output:\n", out if code == 0 else err)

print("\n=== 3. Restarting API container to apply new environment key ===")
cmd_restart = (
    "cd /home/rahul/Provaani_akruti && "
    "sudo docker compose up -d --no-deps api"
)
out, err, code = run_ssh(cmd_restart)
print("Restart API container:\n", out if code == 0 else err)

time.sleep(3)

print("\n=== 4. Testing Cerebras API health from inside API container ===")
test_llm_script = f"""
import httpx, asyncio, json

async def test():
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(
            'https://api.cerebras.ai/v1/chat/completions',
            headers={{'Authorization': 'Bearer {NEW_KEY}', 'Content-Type': 'application/json'}},
            json={{'model': 'llama-3.3-70b', 'messages': [{{'role': 'user', 'content': 'Say hello in 5 words'}}]}}
        )
        print('Cerebras Status:', r.status_code)
        if r.status_code == 200:
            print('Cerebras Response:', r.json()['choices'][0]['message']['content'])
        else:
            print('Cerebras Error:', r.text)

asyncio.run(test())
"""

cmd_write_test = f"cat << 'EOF' > /home/rahul/Provaani_akruti/test_llm_temp.py\n{test_llm_script}\nEOF"
run_ssh(cmd_write_test)

cmd_run_test = (
    "sudo docker cp /home/rahul/Provaani_akruti/test_llm_temp.py provaani_akruti-api-1:/app/test_llm_temp.py && "
    "sudo docker exec provaani_akruti-api-1 python /app/test_llm_temp.py && "
    "sudo docker exec provaani_akruti-api-1 rm -f /app/test_llm_temp.py && "
    "rm -f /home/rahul/Provaani_akruti/test_llm_temp.py"
)
out, err, code = run_ssh(cmd_run_test)
print("LLM Health Test:\n", out if code == 0 else err)
