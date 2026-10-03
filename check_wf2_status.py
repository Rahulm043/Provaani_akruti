import subprocess

cmd = [
    "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
    "-o", "StrictHostKeyChecking=no",
    "rahul@34.131.238.156",
    "sudo docker exec -i provaani_akruti-postgres-1 psql -U postgres -d postgres"
]
sql = "SELECT id, workflow_id, workflow_configurations->'model_configuration_v2_override'->'byok'->'realtime'->'realtime'->>'model' AS model, workflow_configurations->'model_configuration_v2_override'->'byok'->'realtime'->'realtime'->>'voice' AS voice FROM workflow_definitions WHERE workflow_id = 2;\n"
res = subprocess.run(cmd, input=sql, capture_output=True, text=True, errors="replace")
print(res.stdout)
