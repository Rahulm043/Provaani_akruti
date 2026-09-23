import subprocess
import sys
import io

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

run_cmd(["gcloud", "compute", "scp", "inspect_recent_calls.py", f"{VM}:/home/rahul/Provaani_akruti/inspect_recent_calls.py", f"--zone={ZONE}", f"--project={PROJECT}"])

cmd = (
    "sudo docker cp /home/rahul/Provaani_akruti/inspect_recent_calls.py provaani_akruti-api-1:/app/inspect_recent_calls.py && "
    "sudo docker exec provaani_akruti-api-1 python /app/inspect_recent_calls.py && "
    "sudo docker exec provaani_akruti-api-1 rm -f /app/inspect_recent_calls.py && "
    "rm -f /home/rahul/Provaani_akruti/inspect_recent_calls.py"
)
out, err, code = run_ssh(cmd)
print("INSPECT RESULT:\n", out if code == 0 else err)
