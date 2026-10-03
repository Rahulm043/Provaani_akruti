import os
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("CEREBRAS_API_KEY", "CEREBRAS_API_KEY_PLACEHOLDER")

headers = {
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json"
}

candidate_models = [
    "llama-3.3-70b",
    "llama3.3-70b",
    "llama-3.1-70b",
    "llama3.1-70b",
    "llama-3.1-8b",
    "gpt-oss-120b",
    "qwen-3.8-27b"
]

print("Testing candidate models on Cerebras chat completions endpoint...")
for model in candidate_models:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful clinic assistant. Answer in 1 short sentence in English."},
            {"role": "user", "content": "What are the clinic consultation hours?"}
        ],
        "temperature": 0.1,
        "max_tokens": 50
    }
    t0 = time.perf_counter()
    r = requests.post("https://api.cerebras.ai/v1/chat/completions", headers=headers, json=payload)
    dt = time.perf_counter() - t0
    if r.status_code == 200:
        res = r.json()
        reply = res["choices"][0]["message"]["content"]
        time_info = res.get("time_info", {})
        print(f"[OK] Model: {model:<20} | Time: {dt*1000:.1f}ms | Reply: {reply.strip()[:60]} | Speed: {time_info}")
    else:
        print(f"[FAIL] Model: {model:<20} | Status: {r.status_code} | Error: {r.text[:80]}")
