import asyncio
import base64
import json
import requests
import websockets

async def test():
    url = "https://ai-gateway.vercel.sh/v1/realtime/client-secrets"
    headers = {
        "Authorization": "Bearer VERCEL_AI_KEY_PLACEHOLDER",
        "Content-Type": "application/json"
    }
    resp = requests.post(url, headers=headers, json={"model": "google/gemini-3.8-live"})
    token = resp.json()["token"]
    print("Token minted:", token[:20])

    ws_url = "wss://ai-gateway.vercel.sh/v4/ai/realtime-model?ai-model-id=google%2Fgemini-3.8-live"
    subprotocols = ["ai-gateway-realtime.v1", f"ai-gateway-auth.{token}"]
    
    async with websockets.connect(ws_url, subprotocols=subprotocols) as ws:
        print("Connected!")
        
        # 1. Send session-start
        session_start = {
            "type": "session-start",
            "config": {
                "outputModalities": ["audio"],
                "instructions": "Reply with 'Hello from Vercel Gemini Live'.",
                "voice": "Aoede"
            }
        }
        await ws.send(json.dumps(session_start))
        print("Sent session-start:", session_start)
        
        # 2. Send text message
        msg = {
            "type": "conversation-item-create",
            "item": {
                "type": "text-message",
                "role": "user",
                "text": "Hello!"
            }
        }
        await ws.send(json.dumps(msg))
        print("Sent text message:", msg)
        
        # 3. Send response-create
        await ws.send(json.dumps({"type": "response-create"}))
        print("Sent response-create")

        # Listen for up to 10 seconds
        try:
            while True:
                data = await asyncio.wait_for(ws.recv(), timeout=10.0)
                print("RECV:", data[:200])
        except asyncio.TimeoutError:
            print("Timed out waiting for response.")

if __name__ == "__main__":
    asyncio.run(test())
