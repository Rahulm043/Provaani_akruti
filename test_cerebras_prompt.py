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

# Fetch Workflow 1 / 4 prompt from postgres or file
prompt = "You are the AI medical receptionist for Aakruti Aesthetics & Plastic Surgery Clinic. Doctor Kaushal Priya Anand is chief plastic surgeon. Keep answers concise, natural, and helpful. Always offer appointments and clinic details."

payload = {
    "model": "gpt-oss-120b",
    "messages": [
        {"role": "system", "content": prompt},
        {"role": "user", "content": "Can I know about liposuction and clinic timings?"}
    ],
    "temperature": 0.1,
    "max_tokens": 150,
    "stream": False
}

t0 = time.perf_counter()
r = requests.post("https://api.cerebras.ai/v1/chat/completions", headers=headers, json=payload)
dt = time.perf_counter() - t0
print(f"Status: {r.status_code} | Total Latency: {dt*1000:.1f}ms")
if r.status_code == 200:
    res = r.json()
    msg = res["choices"][0]["message"]
    print("Content:", msg.get("content"))
    print("Reasoning:", msg.get("reasoning"))
    print("Time info:", res.get("time_info"))
else:
    print("Error:", r.text)
