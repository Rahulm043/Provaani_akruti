import subprocess

cmd = [
    "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
    "-o", "StrictHostKeyChecking=no",
    "rahul@34.131.238.156",
    "sudo docker logs provaani_akruti-api-1 2>&1 | grep 'run_id=227'"
]
proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
lines = proc.stdout.splitlines()
print(f"Total lines for 227: {len(lines)}")
for line in lines:
    print(line.encode("ascii", "replace").decode("ascii"))
