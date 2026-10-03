import subprocess

cmd = [
    "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
    "-o", "StrictHostKeyChecking=no",
    "rahul@34.131.238.156",
    "sudo docker exec provaani_akruti-api-1 grep -n -C 10 'tool' /app/api/services/pipecat/realtime/gemini_live.py"
]
subprocess.run(cmd)
