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

url = "https://openrouter.ai/api/v1/audio/speech"

# Test WITH speed parameter
payload_with_speed = {
    "model": "google/gemini-3.8-flash-lite-tts",
    "input": "নমস্কার! আকৃতি ক্লিনিক।",
    "voice": "Aoede",
    "response_format": "pcm",
    "speed": 1.0
}
r1 = requests.post(url, headers=headers, json=payload_with_speed)
print("With speed=1.0 Status:", r1.status_code, r1.text)

# Test WITHOUT speed parameter
payload_without_speed = {
    "model": "google/gemini-3.8-flash-lite-tts",
    "input": "নমস্কার! আকৃতি ক্লিনিক।",
    "voice": "Aoede",
    "response_format": "pcm"
}
r2 = requests.post(url, headers=headers, json=payload_without_speed)
print("Without speed Status:", r2.status_code, "Length:", len(r2.content))
