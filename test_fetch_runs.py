import subprocess

cmd = [
    "gcloud", "compute", "ssh", "instance-20260815-072654",
    "--zone=asia-south2-b",
    "--project=project-cb090c10-8c6d-44c8-bbb",
    "--command=python3 -c \"import requests; tok=requests.post('http://localhost:8000/api/v1/auth/login', json={'email':'admin@provaani.xyz','password':'Admin123!'}).json()['token']; print(requests.get('http://localhost:8000/api/v1/workflow/1/runs?limit=3', headers={'Authorization': 'Bearer ' + str(tok)}).json())\""
]
proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", shell=True)
print("Response:\n", proc.stdout)
if proc.stderr:
    print("Stderr:\n", proc.stderr)
