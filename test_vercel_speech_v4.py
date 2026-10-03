import os
import requests
import json
import base64
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("VERCEL_AI_API_KEY", "VERCEL_AI_KEY_PLACEHOLDER")

url = "https://ai-gateway.vercel.sh/v4/ai/speech-model"
headers = {
    "Authorization": f"Bearer {key}",
    "ai-gateway-auth-method": "api-key",
    "ai-gateway-protocol-version": "0.0.1",
    "ai-speech-model-specification-version": "4",
    "ai-model-id": "google/gemini-3.8-flash-lite-tts",
    "Content-Type": "application/json",
    "User-Agent": "ai-sdk/gateway/0.0.1"
}

body = {
    "text": "নমস্কার! আকৃতি নান্দনিক ও প্লাস্টিক সার্জারি ক্লিনিকে আপনাকে স্বাগত। বলুন, আপনাকে কীভাবে সাহায্য করতে পারি?",
    "voice": "Aoede"
}

print("Calling Vercel AI Gateway speech-model endpoint...")
r = requests.post(url, headers=headers, json=body)
print("Status Code:", r.status_code)
print("Headers:", dict(r.headers))
if r.status_code == 200:
    res = r.json()
    audio_b64 = res.get("audio", "")
    audio_bytes = base64.b64decode(audio_b64)
    print(f"Success! Received {len(audio_bytes)} audio bytes.")
    with open("test_vercel_output.mp3", "wb") as f:
        f.write(audio_bytes)
    print("Saved test_vercel_output.mp3")
else:
    print("Error response:", r.text)
