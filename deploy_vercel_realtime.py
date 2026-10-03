import subprocess

print("Uploading updated vercel_realtime.py to VM...")
cmd_scp = [
    "scp", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
    "-o", "StrictHostKeyChecking=no",
    "vercel_realtime.py",
    "rahul@34.131.238.156:/tmp/vercel_realtime.py"
]
subprocess.run(cmd_scp, check=True)

print("Copying into container and verifying import...")
cmd_cp = [
    "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
    "-o", "StrictHostKeyChecking=no",
    "rahul@34.131.238.156",
    "sudo docker cp /tmp/vercel_realtime.py provaani_akruti-api-1:/app/api/services/pipecat/realtime/vercel_realtime.py && "
    "sudo docker restart provaani_akruti-api-1 && "
    "sleep 4 && "
    "sudo docker exec provaani_akruti-api-1 python3 -c 'from api.services.pipecat.realtime.vercel_realtime import DograhVercelRealtimeLLMService; print(\"Import success!\")'"
]
proc = subprocess.run(cmd_cp, capture_output=True, text=True)
print(proc.stdout)
if proc.stderr:
    print("Stderr:", proc.stderr)
