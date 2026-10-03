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

# Fetch models from OpenRouter
print("Fetching OpenRouter models...")
r = requests.get("https://openrouter.ai/api/v1/models", headers=headers)
if r.status_code == 200:
    data = r.json()
    models = data.get("data", [])
    matching = [m for m in models if any(k in m.get("id", "").lower() for k in ["gemini", "tts", "flash-lite", "speech"])]
    print(f"Total matching models found: {len(matching)}")
    for m in matching:
        if "tts" in m.get("id", "").lower() or "flash" in m.get("id", "").lower():
            print(f"- {m.get('id')} | Name: {m.get('name')} | Pricing: {m.get('pricing')}")
else:
    print("Error fetching models:", r.status_code, r.text)
