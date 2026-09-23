#!/usr/bin/env python3
"""
LLM Model Switching and Deployment Tool for Provaani Akruti

Supports switching between:
1. 'openrouter' -> deepseek/deepseek-v4-flash-0731 via OpenRouter
2. 'cerebras'   -> gpt-oss-120b via Cerebras AI

Usage:
  python switch_llm_model.py --model openrouter
  python switch_llm_model.py --model cerebras
  python switch_llm_model.py --status
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path

ZONE = "asia-south2-b"
PROJECT = "project-cb090c10-8c6d-44c8-bbb"
VM = "instance-20260815-072654"

def load_env():
    env_file = Path(".env")
    env_vars = {}
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip()
    return env_vars

ENV = load_env()
CEREBRAS_KEY = ENV.get("CEREBRAS_API_KEY", "")
OPENROUTER_KEY = ENV.get("OPENROUTER_API_KEY", "")
SMALLEST_KEY = ENV.get("SMALLEST_API_KEY", "")

MODELS = {
    "gemini-flash-lite": {
        "name": "Gemini 2.5 Flash Lite (via OpenRouter)",
        "provider": "openrouter",
        "model": "google/gemini-2.5-flash-lite",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": [OPENROUTER_KEY],
        "temperature": 0.1
    },
    "openrouter": {
        "name": "DeepSeek V4 Flash (via OpenRouter)",
        "provider": "openrouter",
        "model": "deepseek/deepseek-v4-flash-0731",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": [OPENROUTER_KEY],
        "temperature": 0.1
    },
    "deepseek-v3": {
        "name": "DeepSeek V3 (via OpenRouter)",
        "provider": "openrouter",
        "model": "deepseek/deepseek-chat",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": [OPENROUTER_KEY],
        "temperature": 0.1
    },
    "cerebras": {
        "name": "GPT-OSS 120B (via Cerebras AI)",
        "provider": "openai",
        "model": "gpt-oss-120b",
        "base_url": "https://api.cerebras.ai/v1",
        "api_key": [CEREBRAS_KEY],
        "temperature": 0.1
    }
}

def run_cmd(cmd):
    proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
    return proc.stdout.strip(), proc.stderr.strip(), proc.returncode

def run_ssh(command):
    cmd = ["gcloud", "compute", "ssh", VM, f"--zone={ZONE}", f"--project={PROJECT}", f"--command={command}"]
    return run_cmd(cmd)

def run_scp(local_path, remote_path):
    cmd = ["gcloud", "compute", "scp", "--recurse", local_path, f"{VM}:{remote_path}", f"--zone={ZONE}", f"--project={PROJECT}"]
    return run_cmd(cmd)

def build_update_script(target_key):
    target_llm = MODELS[target_key]
    script = f"""
import asyncio
import json
from api.db import db_client
from sqlalchemy import text

TARGET_LLM = {json.dumps(target_llm)}

async def main():
    async with db_client.async_session() as session:
        # 1. Update published workflow definition (id=1)
        res = await session.execute(text("SELECT id, workflow_configurations FROM workflow_definitions WHERE workflow_id = 1;"))
        rows = res.fetchall()
        for r in rows:
            def_id = r[0]
            config = r[1]
            if isinstance(config, str):
                config = json.loads(config)
            
            if 'model_configuration_v2_override' in config:
                config['model_configuration_v2_override']['byok']['pipeline']['llm'] = TARGET_LLM
                await session.execute(
                    text("UPDATE workflow_definitions SET workflow_configurations = :cfg WHERE id = :id;"),
                    {{"cfg": json.dumps(config), "id": def_id}}
                )
                print(f"[OK] Updated workflow_definition ID {{def_id}} with {{TARGET_LLM['model']}} ({{TARGET_LLM['provider']}})")

        # 2. Update active workflow (id=1)
        res_wf = await session.execute(text("SELECT id, workflow_configurations FROM workflows WHERE id = 1;"))
        wf_rows = res_wf.fetchall()
        for r in wf_rows:
            wf_id = r[0]
            config = r[1]
            if isinstance(config, str):
                config = json.loads(config)
            
            if 'model_configuration_v2_override' in config:
                config['model_configuration_v2_override']['byok']['pipeline']['llm'] = TARGET_LLM
                await session.execute(
                    text("UPDATE workflows SET workflow_configurations = :cfg WHERE id = :id;"),
                    {{"cfg": json.dumps(config), "id": wf_id}}
                )
                print(f"[OK] Updated workflow ID {{wf_id}} with {{TARGET_LLM['model']}} ({{TARGET_LLM['provider']}})")

        # 3. Update organization_configurations
        res_org = await session.execute(text("SELECT value FROM organization_configurations WHERE key = 'MODEL_CONFIGURATION_V2' AND organization_id = 1;"))
        org_row = res_org.first()
        if org_row:
            org_cfg = org_row[0]
            if isinstance(org_cfg, str):
                org_cfg = json.loads(org_cfg)
            if 'byok' in org_cfg and 'pipeline' in org_cfg['byok']:
                org_cfg['byok']['pipeline']['llm'] = TARGET_LLM
                await session.execute(
                    text("UPDATE organization_configurations SET value = :val WHERE key = 'MODEL_CONFIGURATION_V2' AND organization_id = 1;"),
                    {{"val": json.dumps(org_cfg)}}
                )
                print(f"[OK] Updated organization_configurations MODEL_CONFIGURATION_V2")

        await session.commit()
        print("[SUCCESS] All database records committed.")

asyncio.run(main())
"""
    return script

def check_status():
    status_script = """
import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def main():
    async with db_client.async_session() as session:
        res = await session.execute(text("SELECT id, workflow_configurations FROM workflow_definitions WHERE workflow_id = 1 AND status = 'published';"))
        row = res.first()
        if row:
            cfg = row[1]
            if isinstance(cfg, str):
                cfg = json.loads(cfg)
            llm = cfg.get('model_configuration_v2_override', {}).get('byok', {}).get('pipeline', {}).get('llm', {})
            print(f"ACTIVE LLM: {llm.get('model')} (provider: {llm.get('provider')}, base_url: {llm.get('base_url')})")
        else:
            print("No published workflow found.")

asyncio.run(main())
"""
    tmp_path = Path("scratch_status.py")
    tmp_path.write_text(status_script, encoding="utf-8")
    run_scp(str(tmp_path), "/tmp/check_status.py")
    out, err, _ = run_ssh("sudo docker cp /tmp/check_status.py provaani_akruti-api-1:/app/check_status.py && sudo docker exec provaani_akruti-api-1 python /app/check_status.py")
    print(out)
    if tmp_path.exists():
        tmp_path.unlink()

def switch_model(target_key):
    if target_key not in MODELS:
        print(f"Error: Unknown model '{target_key}'. Available: {list(MODELS.keys())}")
        sys.exit(1)

    target = MODELS[target_key]
    print(f"\n==========================================")
    print(f" Switching LLM Pipeline to: {target['name']}")
    print(f" Model ID: {target['model']}")
    print(f" Base URL: {target['base_url']}")
    print(f"==========================================\n")

    # 1. Sync config & env files to VM
    print("--> 1. Syncing .env, docker-compose.yaml, and warmup_daemon.py to VM...")
    run_scp(".env", "/home/rahul/Provaani_akruti/.env")
    run_scp("docker-compose.yaml", "/home/rahul/Provaani_akruti/docker-compose.yaml")
    run_scp("warmup_daemon.py", "/home/rahul/Provaani_akruti/warmup_daemon.py")

    # 2. Build and run DB update script
    print("--> 2. Applying model configuration in PostgreSQL...")
    script_content = build_update_script(target_key)
    tmp_path = Path("scratch_switch_db.py")
    tmp_path.write_text(script_content, encoding="utf-8")
    run_scp(str(tmp_path), "/tmp/switch_db.py")
    out, err, code = run_ssh("sudo docker cp /tmp/switch_db.py provaani_akruti-api-1:/app/switch_db.py && sudo docker exec provaani_akruti-api-1 python /app/switch_db.py")
    print(out)
    if err and "WARNING" not in err:
        print("STDERR:", err)
    if tmp_path.exists():
        tmp_path.unlink()

    # 3. Reload containers with new env
    print("--> 3. Restarting API container to apply environment variables...")
    run_ssh("cd /home/rahul/Provaani_akruti && sudo docker compose up -d --no-deps api")

    # 4. Trigger warmup
    print("--> 4. Triggering warmup daemon...")
    run_ssh("sudo docker cp /home/rahul/Provaani_akruti/warmup_daemon.py provaani_akruti-api-1:/app/warmup_daemon.py && sudo docker exec provaani_akruti-api-1 python /app/warmup_daemon.py")

    print(f"\n[SUCCESS] Active LLM successfully switched to {target['name']}!")

def main():
    parser = argparse.ArgumentParser(description="Switch LLM Model for Provaani Akruti")
    parser.add_argument("--model", choices=list(MODELS.keys()), help="Target model to activate")
    parser.add_argument("--status", action="store_true", help="Check currently active LLM")
    args = parser.parse_args()

    if args.status:
        check_status()
    elif args.model:
        switch_model(args.model)
    else:
        # Default action: switch to openrouter
        switch_model("openrouter")

if __name__ == "__main__":
    main()
