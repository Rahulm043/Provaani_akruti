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
            "config": {"outputModalities": ["audio"], "instructions": "Hello", "voice": "Aoede"}
        }))
        while True:
            evt = json.loads(await ws.recv())
            if evt.get("type") == "session-created":
                break
        print("Connected and ready. Now sending empty audio...")
        try:
            await ws.send(json.dumps({"type": "input-audio-append", "audio": ""}))
            while True:
                msg = await ws.recv()
                print("Received:", msg)
        except Exception as e:
            print("CAUGHT EXCEPTION ON EMPTY AUDIO:", e)

if __name__ == "__main__":
    asyncio.run(test())
