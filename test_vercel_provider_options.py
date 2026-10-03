import asyncio
import json
import requests
import websockets

def test_client_secrets():
    url = "https://ai-gateway.vercel.sh/v1/realtime/client-secrets"
    headers = {"Authorization": "Bearer VERCEL_AI_KEY_PLACEHOLDER", "Content-Type": "application/json"}
    
    # Try passing providerOptions in client-secrets
    payload = {
        "model": "google/gemini-3.8-live",
        "providerOptions": {
            "google": {
                "contextWindowCompression": {
                    "triggerTokens": 25600,
                    "slidingWindow": {"targetTokens": 12800}
                }
            }
        }
    }
    r = requests.post(url, headers=headers, json=payload)
    print("client-secrets with providerOptions status:", r.status_code, r.text)

async def test_session_update_provider_options():
    url = "https://ai-gateway.vercel.sh/v1/realtime/client-secrets"
    headers = {"Authorization": "Bearer VERCEL_AI_KEY_PLACEHOLDER", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json={"model": "google/gemini-3.8-live"})
    token = resp.json()["token"]
    ws_url = "wss://ai-gateway.vercel.sh/v4/ai/realtime-model?ai-model-id=google%2Fgemini-3.8-live"
    subprotocols = ["ai-gateway-realtime.v1", f"ai-gateway-auth.{token}"]

    async with websockets.connect(ws_url, subprotocols=subprotocols) as ws:
        # First event from Vercel is usually session-created
        initial_evt = json.loads(await ws.recv())
        print("Initial event received:", initial_evt.get("type"))

        msg = {
            "type": "session-update",
            "config": {
                "outputModalities": ["audio"],
                "instructions": "You are a helpful assistant.",
                "voice": "Aoede",
                "providerOptions": {
                    "google": {
                        "contextWindowCompression": {
                            "triggerTokens": 25600,
                            "slidingWindow": {"targetTokens": 12800}
                        }
                    }
                }
            }
        }
        await ws.send(json.dumps(msg))
        print("Sent session-update with providerOptions, waiting to see if connection stays alive or closes...")
        try:
            # Send a ping or small audio or wait 3 seconds
            await asyncio.sleep(2.0)
            print("WebSocket is still OPEN! State:", ws.state)
        except Exception as e:
            print("Failed:", repr(e))

if __name__ == "__main__":
    test_client_secrets()
    asyncio.run(test_session_update_provider_options())
