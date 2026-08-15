import json, requests

# Login
r = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "admin@sukanya.com", "password": "Admin123!"},
)
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

# Get current workflow
r = requests.get("http://localhost:8000/api/v1/workflow/fetch/1", headers=headers)
wf = r.json()
defi = wf["workflow_definition"]

# Remove greeting node (id=1) and its edge
defi["nodes"] = [n for n in defi["nodes"] if n["id"] != "1"]
defi["edges"] = [e for e in defi["edges"] if e["source"] != "1" and e["target"] != "1"]

# Make node 2 the start node
for n in defi["nodes"]:
    if n["id"] == "2":
        n["data"]["is_start"] = True
        n["data"]["delayed_start"] = False
        # Prepend greeting instruction to prompt
        greeting = '## First Turn (Opening)\nStart the conversation with: "Namaskar, ami Riya bolchhi. Provani AI theke calling korchhi. Aapni ki ektu kotha bolte parben?" Wait for them to respond before saying anything else.\n\n'
        n["data"]["prompt"] = greeting + n["data"]["prompt"]

defi["start_node_id"] = "2"

# Update workflow (create new version)
update = {
    "name": wf["name"],
    "description": "Fixed - merged greeting into main conversation",
    "workflow_definition": defi,
}
r = requests.put(
    "http://localhost:8000/api/v1/workflow/update/1",
    json=update,
    headers=headers,
)
print(f"Status: {r.status_code}")
print(r.text[:500] if r.status_code >= 400 else "OK")
