import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("VERCEL_AI_API_KEY", "VERCEL_AI_KEY_PLACEHOLDER")

print("Testing Vercel Speech Endpoints...")

# Test 1: OpenAI-compatible speech endpoint
url1 = "https://ai-gateway.vercel.sh/v1/audio/speech"
headers1 = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}
payload1 = {
    "model": "google/gemini-3.8-flash-lite-tts",
    "input": "নমস্কার! আকৃতি নান্দনিক ও প্লাস্টিক সার্জারি ক্লিনিকে আপনাকে স্বাগত।",
    "voice": "Aoede"
}
r1 = requests.post(url1, headers=headers1, json=payload1)
print(f"Test 1 (/v1/audio/speech) Status: {r1.status_code}")
print(f"Response: {r1.text[:200]}")

# Test 2: Vercel v4 speech endpoint
url2 = "https://ai-gateway.vercel.sh/v4/ai/speech"
headers2 = {
    "Authorization": f"Bearer {key}",
    "ai-gateway-auth-method": "api-key",
    "ai-gateway-protocol-version": "0.0.1",
    "Content-Type": "application/json"
}
payload2 = {
    "model": "google/gemini-3.8-flash-lite-tts",
    "text": "নমস্কার! আকৃতি নান্দনিক ও প্লাস্টিক সার্জারি ক্লিনিকে আপনাকে স্বাগত।",
    "voice": "Aoede"
}
r2 = requests.post(url2, headers=headers2, json=payload2)
print(f"Test 2 (/v4/ai/speech) Status: {r2.status_code}")
print(f"Response: {r2.text[:200]}")

# Test 3: Google Generative Language REST with Vercel Gateway Base URL
url3 = f"https://ai-gateway.vercel.sh/v1beta/models/gemini-3.8-flash-lite-tts:generateContent"
headers3 = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}
payload3 = {
    "contents": [{"parts": [{"text": "নমস্কার! আকৃতি নান্দনিক ও প্লাস্টিক সার্জারি ক্লিনিকে আপনাকে স্বাগত।"}]}],
    "generationConfig": {
        "responseModalities": ["AUDIO"],
        "speechConfig": {
            "voiceConfig": {
                "prebuiltVoiceConfig": {
                    "voiceName": "Aoede"
                }
            }
        }
    }
}
r3 = requests.post(url3, headers=headers3, json=payload3)
print(f"Test 3 (/v1beta/models/...:generateContent) Status: {r3.status_code}")
print(f"Response: {r3.text[:200]}")
