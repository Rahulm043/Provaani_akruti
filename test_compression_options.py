import asyncio
import json
import requests
import websockets

async def test_option(name, config_obj):
    url = "https://ai-gateway.vercel.sh/v1/realtime/client-secrets"
    headers = {"Authorization": "Bearer VERCEL_AI_KEY_PLACEHOLDER", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json={"model": "google/gemini-3.8-live"})
    token = resp.json()["token"]
    ws_url = "wss://ai-gateway.vercel.sh/v4/ai/realtime-model?ai-model-id=google%2Fgemini-3.8-live"
    subprotocols = ["ai-gateway-realtime.v1", f"ai-gateway-auth.{token}"]

    print(f"\n--- Testing: {name} ---")
    try:
        async with websockets.connect(ws_url, subprotocols=subprotocols) as ws:
            await ws.send(json.dumps({
                "type": "session-update",
                "config": config_obj
            }))
            # Wait for response or error
            evt = json.loads(await asyncio.wait_for(ws.recv(), timeout=6.0))
            print(f"SUCCESS: received {evt.get('type')}")
            return True
    except Exception as e:
        print(f"FAILED: {e}")
        return False

async def main():
    base = {"outputModalities": ["audio"], "instructions": "You are a helpful assistant.", "voice": "Aoede"}
    
    # Baseline
    await test_option("Baseline (no extra params)", base)

    # Option 1: providerOptions.google.contextWindowCompression
    opt1 = dict(base)
    opt1["providerOptions"] = {
        "google": {
            "contextWindowCompression": {
                "slidingWindow": {}
            }
        }
    }
    await test_option("providerOptions.google.contextWindowCompression (slidingWindow: {})", opt1)

    # Option 2: providerOptions.google.context_window_compression
    opt2 = dict(base)
    opt2["providerOptions"] = {
        "google": {
            "context_window_compression": {
                "sliding_window": {}
            }
        }
    }
    await test_option("providerOptions.google.context_window_compression (snake_case)", opt2)

    # Option 3: direct contextWindowCompression inside config
    opt3 = dict(base)
    opt3["contextWindowCompression"] = {"slidingWindow": {}}
    await test_option("Direct contextWindowCompression", opt3)

if __name__ == "__main__":
    asyncio.run(main())
