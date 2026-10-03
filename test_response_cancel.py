import asyncio
import json
import requests
import websockets

async def test_response_cancel():
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
        evt = json.loads(await ws.recv())
        print("Connected and session created:", evt.get("type"))

        # Trigger response
        await ws.send(json.dumps({
            "type": "conversation-item-create",
            "item": {"type": "text-message", "role": "user", "text": "Please count slowly from 1 to 20."}
        }))

        # Read some audio deltas
        for _ in range(5):
            msg = await ws.recv()
            print("Received event during generation:", json.loads(msg).get("type"))

        # Now send response-cancel
        print("Sending response-cancel...")
        await ws.send(json.dumps({"type": "response-cancel"}))

        # Check what Vercel sends next
        try:
            for _ in range(5):
                msg = await asyncio.wait_for(ws.recv(), timeout=3.0)
                print("Received after response-cancel:", json.loads(msg).get("type"))
        except websockets.exceptions.ConnectionClosedError as e:
            print("CONNECTION CLOSED ON response-cancel:", e)
        except Exception as e:
            print("Exception after response-cancel:", e)

if __name__ == "__main__":
    asyncio.run(test_response_cancel())
