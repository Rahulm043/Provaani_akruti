import subprocess

cmd = [
    "gcloud", "compute", "ssh", "instance-20260815-072654",
    "--zone=asia-south2-b",
    "--project=project-cb090c10-8c6d-44c8-bbb",
    "--command=sudo docker exec provaani_akruti-api-1 cat /app/api/routes/telephony.py"
]
proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
with open("c:/Users/rahul/Desktop/Provaani_akruti/patches/api/routes/telephony.py", "w", encoding="utf-8") as f:
    f.write(proc.stdout)

print(f"Extracted telephony.py ({len(proc.stdout)} chars)")
