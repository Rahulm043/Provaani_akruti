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

print("=== 1. Syncing custom-ui files to VM ===")
run_scp("custom-ui/src", "/home/rahul/Provaani_akruti/custom-ui/")
run_scp("custom-ui/public", "/home/rahul/Provaani_akruti/custom-ui/")
run_scp("custom-ui/index.html", "/home/rahul/Provaani_akruti/custom-ui/index.html")
run_scp("custom-ui/.dockerignore", "/home/rahul/Provaani_akruti/custom-ui/.dockerignore")
run_scp("custom-ui/Dockerfile", "/home/rahul/Provaani_akruti/custom-ui/Dockerfile")

print("=== 2. Rebuilding and recreating custom-ui container without cache ===")
build_ui = (
    "cd /home/rahul/Provaani_akruti && "
    "sudo docker compose build --no-cache custom-ui && "
    "sudo docker compose up -d --force-recreate --no-deps custom-ui"
)
run_ssh(build_ui)

print("=== 3. Checking custom-ui container status ===")
run_ssh("sudo docker ps | grep custom-ui")
