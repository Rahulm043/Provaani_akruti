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

for m in ["gpt-oss-120b", "qwen-3.8-27b"]:
    payload = {
        "model": m,
        "messages": [
            {"role": "system", "content": "You are a helpful clinic assistant. Answer in 1 short sentence."},
            {"role": "user", "content": "What are the clinic consultation hours?"}
        ],
        "temperature": 0.1,
        "max_tokens": 50
    }
    t0 = time.perf_counter()
    r = requests.post("https://api.cerebras.ai/v1/chat/completions", headers=headers, json=payload)
    dt = time.perf_counter() - t0
    print(f"=== Model: {m} (Status: {r.status_code}, Latency: {dt*1000:.1f}ms) ===")
    if r.status_code == 200:
        print(json.dumps(r.json(), indent=2))
    else:
        print(r.text)
