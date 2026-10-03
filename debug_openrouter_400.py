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

# Test different texts and voice casings
tests = [
    {"model": "google/gemini-3.8-flash-lite-tts", "input": "নমস্কার! আকৃতি নান্দনিক ও প্লাস্টিক সার্জারি ক্লিনিকে আপনাকে স্বাগত।", "voice": "Aoede", "response_format": "pcm"},
    {"model": "google/gemini-3.8-flash-lite-tts", "input": "নমস্কার!", "voice": "Aoede", "response_format": "pcm"},
    {"model": "google/gemini-3.8-flash-lite-tts", "input": "Hello, how can I help you?", "voice": "Aoede", "response_format": "pcm"},
    {"model": "google/gemini-3.8-flash-lite-tts", "input": "नमस्ते, मैं आपकी क्या मदद कर सकता हूँ?", "voice": "Aoede", "response_format": "pcm"},
    {"model": "google/gemini-3.8-flash-lite-tts", "input": "নমস্কার!", "voice": "aoede", "response_format": "pcm"},
]

for i, p in enumerate(tests):
    r = requests.post(url, headers=headers, json=p)
    print(f"Test {i+1}: Status={r.status_code} | Text={r.text[:120] if r.status_code != 200 else f'Success ({len(r.content)} bytes)'}")
