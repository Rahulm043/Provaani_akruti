import subprocess
import json

cmd = 'gcloud compute ssh dograh-vm --zone=asia-south1-a --project=dograh-deployment --account=mappwithsana@gmail.com --command="sudo docker exec dograh_test-postgres-1 psql -U postgres -d postgres -t -A -c \\"SELECT row_to_json(t) FROM (SELECT w.name, w.workflow_configurations as w_conf, wd.workflow_json, wd.workflow_configurations as wd_conf FROM workflows w JOIN workflow_definitions wd ON w.id = wd.workflow_id WHERE w.id = 6 AND wd.status = \'published\') t;\\""'

proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
stdout, stderr = proc.communicate()
res = stdout.decode('utf-8', errors='ignore').strip()

# find JSON in stdout
json_start = res.find('{"name"')
if json_start != -1:
    res = res[json_start:]

data = json.loads(res)
name = data['name']
w_conf = data.get('w_conf') or {}
wf_json = data['workflow_json']
wd_conf = data.get('wd_conf') or {}

print(f"Loaded workflow: {name}")

with open("wf6_data.json", "w", encoding="utf-8") as f:
    json.dump({
        "name": name,
        "w_conf": w_conf,
        "wf_json": wf_json,
        "wd_conf": wd_conf
    }, f, ensure_ascii=False, indent=2)

print("Saved wf6_data.json successfully!")
