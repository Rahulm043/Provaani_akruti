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

# Test 1: OpenRouter speech endpoint
r1 = requests.post("https://openrouter.ai/api/v1/audio/speech", headers=headers, json={"model": "google/gemini-3.8-flash", "input": "Hello", "voice": "Aoede"})
print("1. /api/v1/audio/speech:", r1.status_code, r1.text[:150])

# Test 2: OpenRouter chat completion with modalities
r2 = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json={
    "model": "google/gemini-3.8-flash",
    "messages": [{"role": "user", "content": "Hello"}],
    "modalities": ["text", "audio"],
    "audio": {"voice": "Aoede", "format": "wav"}
})
print("2. /api/v1/chat/completions (modalities):", r2.status_code, r2.text[:150])
