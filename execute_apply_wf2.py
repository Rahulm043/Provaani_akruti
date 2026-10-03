import subprocess

with open("apply_wf2.sql", "rb") as f:
    sql_content = f.read()

cmd = [
    "gcloud", "compute", "ssh", "instance-20260815-072654",
    "--zone=asia-south2-b",
    "--project=project-cb090c10-8c6d-44c8-bbb",
    "--command=sudo docker exec -i provaani_akruti-postgres-1 psql -U postgres -d postgres"
]

proc = subprocess.run(cmd, input=sql_content, capture_output=True, shell=True)
print("Return code:", proc.returncode)
print("Stdout:\n", proc.stdout.decode("utf-8", errors="replace"))
if proc.stderr:
    print("Stderr:\n", proc.stderr.decode("utf-8", errors="replace"))
