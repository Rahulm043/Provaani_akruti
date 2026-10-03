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
        # Test 1: standard Google documentation values (25600 / 12800)
        session_update_1 = {
            "type": "session-update",
            "config": {
                "outputModalities": ["audio"],
                "instructions": "You are a helpful assistant.",
                "voice": "Aoede",
                "contextWindowCompression": {
                    "triggerTokens": 25600,
                    "slidingWindow": {
                        "targetTokens": 12800
                    }
                }
            }
        }
        await ws.send(json.dumps(session_update_1))
        
        while True:
            evt = json.loads(await ws.recv())
            print("Received event:", evt.get("type"), json.dumps(evt)[:200])
            if evt.get("type") == "session-created":
                print("Session created with contextWindowCompression successfully!")
                break

if __name__ == "__main__":
    asyncio.run(test())
