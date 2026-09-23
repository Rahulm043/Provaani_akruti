import base64
import os
import httpx

api_key = os.environ.get("OPENROUTER_API_KEY", "")

with open("/tmp/user_clip.wav", "rb") as f:
    audio_b64 = base64.b64encode(f.read()).decode("utf-8")

payload = {
    "model": "google/gemini-2.5-flash-lite",
    "messages": [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Transcribe this audio recording exactly. Every word or sound spoken by the user. If they spoke Hindi or Bengali, write it in both the original language and English translation.",
                },
                {
                    "type": "input_audio",
                    "input_audio": {
                        "data": audio_b64,
                        "format": "wav",
                    },
                },
            ],
        }
    ],
}

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json",
}

resp = httpx.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=60.0)
print("Status:", resp.status_code)
if resp.status_code == 200:
    data = resp.json()
    print("TRANSCRIPTION OF USER CLIP (48s to 90s):")
    print(data["choices"][0]["message"]["content"])
else:
    print("Error:", resp.text)
