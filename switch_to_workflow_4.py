import subprocess

def switch_to(workflow_id: int):
    print(f"Switching inbound phone routing to Workflow {workflow_id}...")
    cmd = [
        "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
        "-o", "StrictHostKeyChecking=no",
        "rahul@34.131.238.156",
        f"sudo docker exec provaani_akruti-postgres-1 psql -U postgres -d postgres -c 'UPDATE telephony_phone_numbers SET inbound_workflow_id = {workflow_id}; SELECT id, address, inbound_workflow_id FROM telephony_phone_numbers;'"
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    print(proc.stdout)
    if proc.stderr:
        print(proc.stderr)

if __name__ == "__main__":
    switch_to(4)
