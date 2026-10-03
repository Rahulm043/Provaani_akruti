import os, requests, json
from dotenv import load_dotenv

load_dotenv()
key = os.getenv('Google_ai_studio') or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')

r = requests.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}")
print("Status:", r.status_code)
if r.status_code == 200:
    models = r.json().get("models", [])
    print(f"Total models: {len(models)}")
    for m in models:
        name = m.get("name", "")
        methods = m.get("supportedGenerationMethods", [])
        if "speech" in name.lower() or "audio" in name.lower() or "flash" in name.lower() or "3.8" in name.lower() or "live" in name.lower():
            print(f"- {name}: {methods}")
else:
    print("Error:", r.text[:300])
