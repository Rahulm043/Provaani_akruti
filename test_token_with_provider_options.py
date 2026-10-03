import asyncio
import json
import requests
import websockets

async def test_token_with_provider_options():
    url = "https://ai-gateway.vercel.sh/v1/realtime/client-secrets"
    headers = {"Authorization": "Bearer VERCEL_AI_KEY_PLACEHOLDER", "Content-Type": "application/json"}
    
    # Pass contextWindowCompression in providerOptions to client-secrets
    payload = {
        "model": "google/gemini-3.8-live",
        "providerOptions": {
            "google": {
                "contextWindowCompression": {
                    "slidingWindow": {}
                }
            }
        }
    }
    resp = requests.post(url, headers=headers, json=payload)
    print("client-secrets status:", resp.status_code)
    token = resp.json()["token"]
    
    ws_url = "wss://ai-gateway.vercel.sh/v4/ai/realtime-model?ai-model-id=google%2Fgemini-3.8-live"
    subprotocols = ["ai-gateway-realtime.v1", f"ai-gateway-auth.{token}"]

    async with websockets.connect(ws_url, subprotocols=subprotocols) as ws:
        # Send standard session-update
        await ws.send(json.dumps({
            "type": "session-update",
            "config": {"outputModalities": ["audio"], "instructions": "Hello", "voice": "Aoede"}
        }))
        msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
        print("Received:", msg)

if __name__ == "__main__":
    asyncio.run(test_token_with_provider_options())
