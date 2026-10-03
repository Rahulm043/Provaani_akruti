import asyncio
import json
import requests
import websockets

async def test_payload(name, session_update_payload):
    url = "https://ai-gateway.vercel.sh/v1/realtime/client-secrets"
    headers = {"Authorization": "Bearer VERCEL_AI_KEY_PLACEHOLDER", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json={"model": "google/gemini-3.8-live"})
    token = resp.json()["token"]
    ws_url = "wss://ai-gateway.vercel.sh/v4/ai/realtime-model?ai-model-id=google%2Fgemini-3.8-live"
    subprotocols = ["ai-gateway-realtime.v1", f"ai-gateway-auth.{token}"]

    print(f"\n==========================================")
    print(f"TESTING: {name}")
    print(f"Payload: {json.dumps(session_update_payload)}")
    try:
        async with websockets.connect(ws_url, subprotocols=subprotocols) as ws:
            await ws.send(json.dumps(session_update_payload))
            msg = await asyncio.wait_for(ws.recv(), timeout=4.0)
            print(f"RESULT: SUCCESS! Received -> {msg[:200]}")
            return True
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"RESULT: CONNECTION CLOSED ERROR -> {e}")
        return False
    except Exception as e:
        print(f"RESULT: EXCEPTION -> {type(e).__name__}: {e}")
        return False

async def main():
    # 1. Baseline
    await test_payload("Baseline", {
        "type": "session-update",
        "config": {"outputModalities": ["audio"], "instructions": "Hello", "voice": "Aoede"}
    })

    # 2. direct contextWindowCompression inside config (Google standard)
    await test_payload("Direct contextWindowCompression inside config", {
        "type": "session-update",
        "config": {
            "outputModalities": ["audio"],
            "instructions": "Hello",
            "voice": "Aoede",
            "contextWindowCompression": {
                "slidingWindow": {}
            }
        }
    })

    # 3. context_window_compression snake_case inside config
    await test_payload("Direct context_window_compression (snake_case) inside config", {
        "type": "session-update",
        "config": {
            "outputModalities": ["audio"],
            "instructions": "Hello",
            "voice": "Aoede",
            "context_window_compression": {
                "sliding_window": {}
            }
        }
    })

    # 4. providerOptions.google.contextWindowCompression
    await test_payload("providerOptions.google.contextWindowCompression", {
        "type": "session-update",
        "config": {
            "outputModalities": ["audio"],
            "instructions": "Hello",
            "voice": "Aoede",
            "providerOptions": {
                "google": {
                    "contextWindowCompression": {
                        "slidingWindow": {}
                    }
                }
            }
        }
    })

    # 5. providerOptions.google.context_window_compression
    await test_payload("providerOptions.google.context_window_compression (snake_case)", {
        "type": "session-update",
        "config": {
            "outputModalities": ["audio"],
            "instructions": "Hello",
            "voice": "Aoede",
            "providerOptions": {
                "google": {
                    "context_window_compression": {
                        "sliding_window": {}
                    }
                }
            }
        }
    })

    # 6. contextWindowCompression at top level of session-update
    await test_payload("contextWindowCompression at top level of session-update", {
        "type": "session-update",
        "config": {"outputModalities": ["audio"], "instructions": "Hello", "voice": "Aoede"},
        "contextWindowCompression": {
            "slidingWindow": {}
        }
    })

    # 7. raw setup frame
    await test_payload("raw setup frame inside session-update", {
        "type": "session-update",
        "config": {"outputModalities": ["audio"], "instructions": "Hello", "voice": "Aoede"},
        "raw": {
            "setup": {
                "model": "models/gemini-3.8-live",
                "generationConfig": {
                    "responseModalities": ["AUDIO"]
                },
                "contextWindowCompression": {
                    "slidingWindow": {}
                }
            }
        }
    })

if __name__ == "__main__":
    asyncio.run(main())
