import json
import subprocess

def fix_workflow_2():
    # 1. Fetch current workflow_json for workflow 2
    cmd = [
        "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
        "-o", "StrictHostKeyChecking=no",
        "rahul@34.131.238.156",
        "sudo docker exec -i provaani_akruti-postgres-1 psql -U postgres -d postgres -t -A -c \"SELECT workflow_json FROM workflow_definitions WHERE workflow_id = 2;\""
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
    if res.returncode != 0:
        print("Failed to fetch workflow 2:", res.stderr)
        return

    wf_json = json.loads(res.stdout.strip())
    
    # 2. In nodes, find node 1 and remove 'e5528490-e765-401c-9be2-ae4c8d0eea57' from tool_uuids
    END_CALL_UUID = "e5528490-e765-401c-9be2-ae4c8d0eea57"
    for node in wf_json.get("nodes", []):
        tool_uuids = node.get("data", {}).get("tool_uuids", [])
        if END_CALL_UUID in tool_uuids:
            print(f"Removing {END_CALL_UUID} from node {node['id']} tool_uuids")
            node["data"]["tool_uuids"] = [u for u in tool_uuids if u != END_CALL_UUID]

    updated_json_str = json.dumps(wf_json)
    escaped_json = updated_json_str.replace("'", "''")

    sql = f"""UPDATE workflow_definitions SET workflow_json = '{escaped_json}'::json WHERE workflow_id = 2;
SELECT id, workflow_id, json_array_length(workflow_json->'nodes') AS node_count FROM workflow_definitions WHERE workflow_id = 2;
"""
    cmd_update = [
        "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
        "-o", "StrictHostKeyChecking=no",
        "rahul@34.131.238.156",
        "sudo docker exec -i provaani_akruti-postgres-1 psql -U postgres -d postgres"
    ]
    res_update = subprocess.run(cmd_update, input=sql, capture_output=True, text=True, errors="replace")
    print("DB Update result:", res_update.stdout)
    if res_update.stderr:
        print("DB Update stderr:", res_update.stderr)

if __name__ == "__main__":
    fix_workflow_2()
