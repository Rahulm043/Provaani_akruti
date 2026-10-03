import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("CEREBRAS_API_KEY", "CEREBRAS_API_KEY_PLACEHOLDER")

headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

print("Querying Cerebras API for available models...")
r = requests.get("https://api.cerebras.ai/v1/models", headers=headers)
print("Status Code:", r.status_code)
if r.status_code == 200:
    data = r.json()
    models = data.get("data", [])
    print(f"Total models available on Cerebras: {len(models)}\n")
    for m in models:
        print(f"- ID: {m.get('id')} | Created: {m.get('created')} | Owned By: {m.get('owned_by')}")
else:
    print("Error querying Cerebras models:", r.text)
