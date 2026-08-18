import subprocess
import os

ZONE = "asia-south2-b"
PROJECT = "project-cb090c10-8c6d-44c8-bbb"
VM = "instance-20260815-072654"

def run_ssh(cmd_str):
    print(f"--> SSH: {cmd_str}")
    cmd = ["gcloud", "compute", "ssh", VM, f"--zone={ZONE}", f"--project={PROJECT}", f"--command={cmd_str}"]
    proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)
    return proc.returncode

def run_scp(local_path, remote_path):
    print(f"--> SCP {local_path} -> {remote_path}")
    cmd = ["gcloud", "compute", "scp", "--recurse", local_path, f"{VM}:{remote_path}", f"--zone={ZONE}", f"--project={PROJECT}"]
    proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
    if proc.stdout:
        print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)
    return proc.returncode

print("=== 1. Syncing patches & Dockerfile.api & .env ===")
run_scp("patches", "/home/rahul/Provaani_akruti/")
run_scp("Dockerfile.api", "/home/rahul/Provaani_akruti/Dockerfile.api")
run_scp(".env", "/home/rahul/Provaani_akruti/.env")

print("=== 2. Rebuilding and recreating API container ===")
build_api = (
    "cd /home/rahul/Provaani_akruti && "
    "sudo docker build -t dograhtest-custom-api:latest -f Dockerfile.api . && "
    "sudo docker compose up -d --no-deps api"
)
run_ssh(build_api)

print("=== 3. Cleaning up DB ghost records ===")
clean_db = "sudo docker exec provaani_akruti-postgres-1 psql -U postgres -d postgres -c \"DELETE FROM workflow_runs WHERE state = 'initialized' AND is_completed = false;\""
run_ssh(clean_db)

print("=== 4. Syncing custom-ui to VM ===")
run_scp("custom-ui/src", "/home/rahul/Provaani_akruti/custom-ui/")

print("=== 5. Rebuilding and restarting custom-ui container ===")
build_ui = (
    "cd /home/rahul/Provaani_akruti && sudo docker compose build custom-ui && sudo docker compose up -d --no-deps custom-ui"
)
run_ssh(build_ui)

print("=== 6. Checking container statuses ===")
run_ssh("sudo docker ps | grep -E 'custom-ui|api'")
