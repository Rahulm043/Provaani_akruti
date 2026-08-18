import subprocess

cmd = [
    "gcloud", "compute", "ssh", "instance-20260815-072654",
    "--zone=asia-south2-b",
    "--project=project-cb090c10-8c6d-44c8-bbb",
    "--command=sudo docker exec provaani_akruti-api-1 sed -n '810,860p' /app/api/routes/telephony.py"
]
proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
print("parse_inbound_webhook:\n", proc.stdout)
