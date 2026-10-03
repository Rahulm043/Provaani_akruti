import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("VERCEL_AI_API_KEY", "VERCEL_AI_KEY_PLACEHOLDER")

print("Testing Vercel AI Gateway for gemini-3.8-flash-lite-tts...")

headers_bearer = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

# Test 1: OpenAI chat completion with audio output
payload_chat_audio = {
    "model": "google/gemini-3.8-flash-lite-tts",
    "messages": [{"role": "user", "content": "নমস্কার! আকৃতি নান্দনিক ও প্লাস্টিক সার্জারি ক্লিনিকে আপনাকে স্বাগত।"}],
    "modalities": ["text", "audio"],
    "audio": {"voice": "Aoede", "format": "wav"}
}
try:
    r = requests.post("https://ai-gateway.vercel.sh/v1/chat/completions", headers=headers_bearer, json=payload_chat_audio, timeout=10)
    print("1. /v1/chat/completions:", r.status_code, r.text[:200])
except Exception as e:
    print("1. /v1/chat/completions error:", e)

# Test 2: Google SDK generateContent format via /v1/models/google/gemini-3.8-flash-lite-tts:generateContent
endpoints = [
    "https://ai-gateway.vercel.sh/v1/models/google/gemini-3.8-flash-lite-tts:generateContent",
    "https://ai-gateway.vercel.sh/v1/models/gemini-3.8-flash-lite-tts:generateContent",
    "https://ai-gateway.vercel.sh/v1/google/gemini-3.8-flash-lite-tts:generateContent",
    "https://ai-gateway.vercel.sh/v1beta/models/google/gemini-3.8-flash-lite-tts:generateContent",
    "https://ai-gateway.vercel.sh/v1beta/models/gemini-3.8-flash-lite-tts:generateContent",
    "https://ai-gateway.vercel.sh/google/v1beta/models/gemini-3.8-flash-lite-tts:generateContent",
    "https://ai-gateway.vercel.sh/v4/ai/speech-model",
    "https://ai-gateway.vercel.sh/v4/ai/speech",
    "https://ai-gateway.vercel.sh/v1/audio/transcriptions",
    "https://ai-gateway.vercel.sh/v1/audio/speech",
]

payload_genai = {
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

for ep in endpoints:
    try:
        r = requests.post(ep, headers=headers_bearer, json=payload_genai, timeout=10)
        print(f"Endpoint: {ep} -> Status: {r.status_code} | Text: {r.text[:150]}")
    except Exception as e:
        print(f"Endpoint: {ep} -> Error: {e}")
