import os, requests, json
from dotenv import load_dotenv

load_dotenv()
key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
print("Testing direct Google AI Studio API for gemini-3.8-flash-lite-tts...")

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.8-flash-lite-tts:generateContent?key={key}"
payload = {
    "contents": [{
        "parts": [{
            "text": "Namaste! Welcome to Akruti Aesthetics Clinic."
        }]
    }],
    "speechConfig": {
        "voiceConfig": {
            "prebuiltVoiceConfig": {
                "voiceName": "Kore"
            }
        }
    }
}

r = requests.post(url, json=payload)
print("Status code:", r.status_code)
if r.status_code == 200:
    res = r.json()
    print("Keys in response:", list(res.keys()))
    candidates = res.get("candidates", [])
    if candidates:
        parts = candidates[0].get("content", {}).get("parts", [])
        print("Candidate parts count:", len(parts))
        for p in parts:
            if "inlineData" in p:
                print("inlineData mimeType:", p["inlineData"].get("mimeType"))
                print("inlineData data length:", len(p["inlineData"].get("data", "")))
else:
    print("Error:", r.text[:400])
