import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("VERCEL_AI_API_KEY", "VERCEL_AI_KEY_PLACEHOLDER")

url = "https://ai-gateway.vercel.sh/v4/ai/speech-model"

models_to_test = [
    "google/gemini-3.8-flash-lite-tts",
    "google/gemini-3.8-flash-tts",
    "openai/tts-1",
    "openai/tts-1-hd",
    "fish-audio/s1"
]

for m in models_to_test:
    headers = {
        "Authorization": f"Bearer {key}",
        "ai-gateway-auth-method": "api-key",
        "ai-gateway-protocol-version": "0.0.1",
        "ai-speech-model-specification-version": "4",
        "ai-model-id": m,
        "Content-Type": "application/json",
        "User-Agent": "ai-sdk/gateway/0.0.1"
    }
    body = {
        "text": "নমস্কার! আকৃতি ক্লিনিক।",
        "voice": "Aoede" if "google" in m else ("alloy" if "openai" in m else "default")
    }
    r = requests.post(url, headers=headers, json=body)
    print(f"Model: {m} -> Status: {r.status_code} | Body: {r.text[:120]}")
