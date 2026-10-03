import asyncio
import base64
import json
import math
import struct
import requests
import websockets

def generate_sine_pcm(freq=440, duration_s=1.0, sample_rate=16000):
    num_samples = int(duration_s * sample_rate)
    data = bytearray()
    for i in range(num_samples):
        val = int(16000 * math.sin(2 * math.pi * freq * (i / sample_rate)))
        data.extend(struct.pack("<h", val))
    return bytes(data)

async def test():
    url = "https://ai-gateway.vercel.sh/v1/realtime/client-secrets"
    headers = {
        "Authorization": "Bearer VERCEL_AI_KEY_PLACEHOLDER",
        "Content-Type": "application/json"
    }
    resp = requests.post(url, headers=headers, json={"model": "google/gemini-3.8-live"})
    token = resp.json()["token"]
    ws_url = "wss://ai-gateway.vercel.sh/v4/ai/realtime-model?ai-model-id=google%2Fgemini-3.8-live"
    subprotocols = ["ai-gateway-realtime.v1", f"ai-gateway-auth.{token}"]
    
    async with websockets.connect(ws_url, subprotocols=subprotocols) as ws:
        print("Connected!")
        
        session_update = {
            "type": "session-update",
            "config": {
                "outputModalities": ["audio"],
                "instructions": "You are a helpful assistant. Reply with one short word.",
                "voice": "Aoede"
            }
        }
        await ws.send(json.dumps(session_update))
        
        while True:
            msg = await ws.recv()
            evt = json.loads(msg)
            print("Received event:", evt.get("type"))
            if evt.get("type") == "session-created":
                break

        # Now send audio append
        pcm = generate_sine_pcm(freq=300, duration_s=0.5, sample_rate=16000)
        b64 = base64.b64encode(pcm).decode("ascii")
        print("Sending input-audio-append...")
        await ws.send(json.dumps({"type": "input-audio-append", "audio": b64}))
        
        print("Sending input-audio-commit...")
        await ws.send(json.dumps({"type": "input-audio-commit"}))
        
        print("Waiting for response...")
        for _ in range(10):
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                evt = json.loads(msg)
                print("Event after audio commit:", evt.get("type"), json.dumps(evt)[:200])
            except asyncio.TimeoutError:
                print("Timeout waiting for more events")
                break

if __name__ == "__main__":
    asyncio.run(test())
