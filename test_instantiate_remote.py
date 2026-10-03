import subprocess

cmd = [
    "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
    "-o", "StrictHostKeyChecking=no",
    "rahul@34.131.238.156",
    """sudo docker exec provaani_akruti-api-1 python3 -c "
import pipecat.services.google.gemini_live.llm as m
import inspect
for line in inspect.getsourcelines(m)[0][35:80]:
    if 'import' in line or 'Settings' in line or 'NOT_GIVEN' in line:
        print(line.strip())
" """
]
proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
print("STDOUT:", proc.stdout.encode("ascii", "replace").decode("ascii"))
print("STDERR:", proc.stderr.encode("ascii", "replace").decode("ascii"))
