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
print("Auth Key Info Status:", r.status_code)
if r.status_code == 200:
    print("Key Info:", json.dumps(r.json(), indent=2))
else:
    print("Error:", r.text)

r2 = requests.get("https://openrouter.ai/api/v1/credits", headers=headers)
print("\nCredits Info Status:", r2.status_code)
if r2.status_code == 200:
    print("Credits Info:", json.dumps(r2.json(), indent=2))
else:
    print("Error:", r2.text)
