import asyncio
import json
import requests
import websockets

async def inspect_function_call_events():
    url = "https://ai-gateway.vercel.sh/v1/realtime/client-secrets"
    headers = {"Authorization": "Bearer VERCEL_AI_KEY_PLACEHOLDER", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json={"model": "google/gemini-3.8-live"})
    token = resp.json()["token"]
    ws_url = "wss://ai-gateway.vercel.sh/v4/ai/realtime-model?ai-model-id=google%2Fgemini-3.8-live"
    subprotocols = ["ai-gateway-realtime.v1", f"ai-gateway-auth.{token}"]

    tools = [
        {
            "type": "function",
            "name": "send_whatsapp",
            "description": "Send clinic details via WhatsApp to caller",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone_number": {"type": "string", "description": "10 digit phone"}
                },
                "required": ["phone_number"]
            }
        }
    ]

    async with websockets.connect(ws_url, subprotocols=subprotocols) as ws:
        cfg = {
            "outputModalities": ["audio"],
            "instructions": "You are a clinic receptionist. When user asks for WhatsApp details, call send_whatsapp tool immediately.",
            "voice": "Aoede",
            "tools": tools
        }

        await ws.send(json.dumps({"type": "session-update", "config": cfg}))
        evt1 = json.loads(await ws.recv())
        print("Setup complete:", evt1.get("type"))

        # Trigger user request
        print("Sending user request...")
        await ws.send(json.dumps({
            "type": "conversation-item-create",
            "item": {"type": "text-message", "role": "user", "text": "Please send WhatsApp details to 9876543210 right now."}
        }))

        # Print all subsequent events
        for i in range(15):
            msg = await ws.recv()
            evt = json.loads(msg)
            print(f"Event {i}: type={evt.get('type')}, rawType={evt.get('rawType')}, keys={list(evt.keys())}")
            if "function" in evt.get("type", "") or "tool" in str(evt):
                print("   -> FULL EVENT:", json.dumps(evt)[:300])
            if evt.get("type") in ("response-done", "audio-done"):
                break

if __name__ == "__main__":
    asyncio.run(inspect_function_call_events())
