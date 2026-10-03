import asyncio
import base64
import json
import requests
import websockets
from pipecat.audio.utils import create_stream_resampler

async def test():
    url = "https://ai-gateway.vercel.sh/v1/realtime/client-secrets"
    headers = {"Authorization": "Bearer VERCEL_AI_KEY_PLACEHOLDER", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json={"model": "google/gemini-3.8-live"})
    token = resp.json()["token"]
    ws_url = "wss://ai-gateway.vercel.sh/v4/ai/realtime-model?ai-model-id=google%2Fgemini-3.8-live"
    subprotocols = ["ai-gateway-realtime.v1", f"ai-gateway-auth.{token}"]

    resampler = create_stream_resampler()

    async with websockets.connect(ws_url, subprotocols=subprotocols) as ws:
        await ws.send(json.dumps({
            "type": "session-update",
            "config": {"outputModalities": ["audio"], "instructions": "You are a receptionist.", "voice": "Aoede"}
        }))
        while True:
            evt = json.loads(await ws.recv())
            if evt.get("type") == "session-created":
                break
        
        # Trigger greeting
        await ws.send(json.dumps({
            "type": "conversation-item-create",
            "item": {"type": "text-message", "role": "user", "text": "Call connected. Please say hello."}
        }))
        
        # Drain greeting
        while True:
            evt = json.loads(await ws.recv())
            if evt.get("type") in ("audio-done", "response-done"):
                break
        print("Greeting drained successfully!")

        # Now simulate streaming 8kHz audio (like Asterisk telephony: 160 samples = 320 bytes every 20ms)
        chunk_8k = b"\x00" * 320
        for i in range(150): # 3 seconds
            chunk_16k = await resampler.resample(chunk_8k, 8000, 16000)
            if not chunk_16k:
                continue
            b64 = base64.b64encode(chunk_16k).decode("ascii")
            print(f"Sending non-empty chunk {i}: len={len(chunk_16k)} bytes...")
            await ws.send(json.dumps({"type": "input-audio-append", "audio": b64}))
            await asyncio.sleep(0.02)
        print("Sent 150 audio chunks (8k->16k) successfully!")
        
        # Now send commit
        await ws.send(json.dumps({"type": "input-audio-commit"}))
        print("Sent commit successfully!")

        for _ in range(5):
            evt = json.loads(await ws.recv())
            print("Received after commit:", evt.get("type"))

if __name__ == "__main__":
    asyncio.run(test())
