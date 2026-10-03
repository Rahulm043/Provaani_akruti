import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("OPENROUTER_API_KEY", "OPENROUTER_API_KEY_PLACEHOLDER")

headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

r = requests.get("https://openrouter.ai/api/v1/auth/key", headers=headers)
print("Key Info:", json.dumps(r.json(), indent=2))

r2 = requests.get("https://openrouter.ai/api/v1/credits", headers=headers)
print("Credits Info:", json.dumps(r2.json(), indent=2))
