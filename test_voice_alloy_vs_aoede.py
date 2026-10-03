import os
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("OPENROUTER_API_KEY", "OPENROUTER_API_KEY_PLACEHOLDER")

headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

url = "https://openrouter.ai/api/v1/audio/speech"

# Test with alloy voice
payload_alloy = {
    "model": "google/gemini-3.8-flash-lite-tts",
    "input": "নমস্কার! আকৃতি ক্লিনিক।",
    "voice": "alloy",
    "response_format": "pcm"
}
r1 = requests.post(url, headers=headers, json=payload_alloy)
print("With voice='alloy': Status =", r1.status_code, "Body =", r1.text)

# Test with Aoede voice
payload_aoede = {
    "model": "google/gemini-3.8-flash-lite-tts",
    "input": "নমস্কার! আকৃতি ক্লিনিক।",
    "voice": "Aoede",
    "response_format": "pcm"
}
r2 = requests.post(url, headers=headers, json=payload_aoede)
print("With voice='Aoede': Status =", r2.status_code, "Length =", len(r2.content))
