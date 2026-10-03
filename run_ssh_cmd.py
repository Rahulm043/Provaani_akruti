import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

def run_ssh(remote_cmd: str):
    full_cmd = [
        "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
        "-o", "StrictHostKeyChecking=no",
        "rahul@34.131.238.156",
        remote_cmd
    ]
    res = subprocess.run(full_cmd, capture_output=True, text=True, errors="replace")
    if res.stdout:
        print("STDOUT:", res.stdout)
    if res.stderr:
        print("STDERR:", res.stderr)
    return res.returncode

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "uname -a"
    sys.exit(run_ssh(cmd))
