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

# Test 1: Standard text chat completion
payload1 = {
    "model": "google/gemini-3.8-flash-lite-tts",
    "messages": [{"role": "user", "content": "নমস্কার! আকৃতি ক্লিনিক।"}]
}
r1 = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload1)
print("1. Standard Chat Completion Status:", r1.status_code)
print("Response:", r1.text[:300])

# Test 2: Audio output chat completion
payload2 = {
    "model": "google/gemini-3.8-flash-lite-tts",
    "messages": [{"role": "user", "content": "নমস্কার! আকৃতি ক্লিনিক।"}],
    "modalities": ["text", "audio"],
    "audio": {
        "voice": "Aoede",
        "format": "wav"
    }
}
r2 = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload2)
print("\n2. Audio Modalities Status:", r2.status_code)
print("Response:", r2.text[:300])
