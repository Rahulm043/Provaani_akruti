import asyncio
import json
import requests
import websockets

async def test():
    # 1. Mint token
    url = "https://ai-gateway.vercel.sh/v1/realtime/client-secrets"
    headers = {
        "Authorization": "Bearer VERCEL_AI_KEY_PLACEHOLDER",
        "Content-Type": "application/json"
    }
    resp = requests.post(url, headers=headers, json={"model": "google/gemini-3.8-live"})
    token = resp.json()["token"]
    print("[1] Minted token successfully!")

    # 2. Connect via WebSockets
    ws_url = "wss://ai-gateway.vercel.sh/v4/ai/realtime-model?ai-model-id=google%2Fgemini-3.8-live"
    subprotocols = ["ai-gateway-realtime.v1", f"ai-gateway-auth.{token}"]
    
    async with websockets.connect(ws_url, subprotocols=subprotocols) as ws:
        print("[2] Connected to Vercel AI Gateway WebSocket via Python!")
        
        # 3. Send session-update
        session_event = {
            "type": "session-update",
            "config": {
                "outputModalities": ["audio"],
                "instructions": "You are a helpful assistant. Reply with one word: Hello.",
                "voice": "Aoede"
            }
        }
        await ws.send(json.dumps(session_event))
        print("[3] Sent session-update!")

        # 4. Send user text message
        msg_event = {
            "type": "conversation-item-create",
            "item": {
                "type": "text-message",
                "role": "user",
                "text": "Hello, are you there?"
            }
        }
        await ws.send(json.dumps(msg_event))
        await ws.send(json.dumps({"type": "response-create"}))
        print("[4] Sent conversation-item-create and response-create!")

        # 5. Receive events
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
            event = json.loads(raw)
            ev_type = event.get("type")
            print(f"Received event from Vercel: {ev_type}")
            if ev_type == "audio-delta":
                delta = event.get("delta", "")
                print(f"  -> Audio chunk received! (length: {len(delta)})")
            elif ev_type == "audio-transcript-delta":
                print(f"  -> Transcript: {event.get('delta')}")
            elif ev_type == "response-done":
                print("  -> Response completed! Usage:", event.get("raw", {}).get("usageMetadata"))
                break

if __name__ == "__main__":
    asyncio.run(test())
