import asyncio
import json
import requests
import websockets

async def test():
    url = "https://ai-gateway.vercel.sh/v1/realtime/client-secrets"
    headers = {"Authorization": "Bearer VERCEL_AI_KEY_PLACEHOLDER", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json={"model": "google/gemini-3.8-live"})
    token = resp.json()["token"]
    ws_url = "wss://ai-gateway.vercel.sh/v4/ai/realtime-model?ai-model-id=google%2Fgemini-3.8-live"
    subprotocols = ["ai-gateway-realtime.v1", f"ai-gateway-auth.{token}"]

    async with websockets.connect(ws_url, subprotocols=subprotocols) as ws:
        await ws.send(json.dumps({
            "type": "session-update",
            "config": {"outputModalities": ["audio"], "instructions": "Speak a very long paragraph.", "voice": "Aoede"}
        }))
        while True:
            evt = json.loads(await ws.recv())
            if evt.get("type") == "session-created":
                break
        
        await ws.send(json.dumps({
            "type": "conversation-item-create",
            "item": {"type": "text-message", "role": "user", "text": "Tell me a long story about Kolkata."}
        }))
        
        # Wait for first audio-delta
        while True:
            evt = json.loads(await ws.recv())
            if evt.get("type") == "audio-delta":
                print("Received first audio delta! Sending response-cancel...")
                break
        
        try:
            await ws.send(json.dumps({"type": "response-cancel"}))
            print("Sent response-cancel. Waiting for next event or rejection...")
            for _ in range(5):
                msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                evt = json.loads(msg)
                print("Event after cancel:", evt.get("type"))
        except Exception as e:
            print("EXCEPTION ON CANCEL:", e)

if __name__ == "__main__":
    asyncio.run(test())
