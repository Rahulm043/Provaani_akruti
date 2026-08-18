import subprocess
import os

# Sync custom-ui to VM
cmd_scp = [
    "gcloud", "compute", "scp", "--recurse",
    "--zone=asia-south2-b",
    "--project=project-cb090c10-8c6d-44c8-bbb",
    "c:/Users/rahul/Desktop/Provaani_akruti/custom-ui",
    "instance-20260815-072654:/home/rahul/Provaani_akruti/"
]
proc_scp = subprocess.run(cmd_scp, capture_output=True, text=True, errors="replace", shell=True)
print("SCP custom-ui:\n", proc_scp.stdout, proc_scp.stderr)

# Build and restart docker container on VM
cmd_build = [
    "gcloud", "compute", "ssh", "instance-20260815-072654",
    "--zone=asia-south2-b",
    "--project=project-cb090c10-8c6d-44c8-bbb",
    "--command=cd /home/rahul/Provaani_akruti/custom-ui && sudo docker build -t provaani_akruti-custom-ui . && sudo docker restart dograhtest-custom-ui"
]
proc_build = subprocess.run(cmd_build, capture_output=True, text=True, errors="replace", shell=True)
print("Build & Restart:\n", proc_build.stdout, proc_build.stderr)
