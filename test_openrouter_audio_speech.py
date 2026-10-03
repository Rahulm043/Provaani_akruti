import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("OPENROUTER_API_KEY", "OPENROUTER_API_KEY_PLACEHOLDER")

headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://akruti.provaani.xyz",
    "X-Title": "Akruti Voice"
}

url = "https://openrouter.ai/api/v1/audio/speech"

payload = {
    "model": "google/gemini-3.8-flash-lite-tts",
    "input": "নমস্কার! আকৃতি নান্দনিক ও প্লাস্টিক সার্জারি ক্লিনিকে আপনাকে স্বাগত। বলুন, আপনাকে কীভাবে সাহায্য করতে পারি?",
    "voice": "Aoede",
    "response_format": "pcm"
}

print("Testing OpenRouter /api/v1/audio/speech with response_format='pcm'...")
r = requests.post(url, headers=headers, json=payload)
print("Status Code:", r.status_code)
print("Response Headers:", dict(r.headers))
if r.status_code == 200:
    print(f"🎉 SUCCESS! Received {len(r.content)} bytes of PCM audio from OpenRouter!")
    with open("test_openrouter_tts.pcm", "wb") as f:
        f.write(r.content)
    print("Saved test_openrouter_tts.pcm successfully!")
else:
    print("Error response:", r.text)
