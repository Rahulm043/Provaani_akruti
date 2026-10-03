import asyncio
import json
import requests
import websockets

async def test_tools(initial: bool):
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
        },
        {
            "type": "function",
            "name": "end_call",
            "description": "End the call gracefully when caller says bye",
            "parameters": {"type": "object", "properties": {}}
        }
    ]

    print(f"\n==========================================")
    print(f"TEST: Tools in INITIAL session-update = {initial}")
    async with websockets.connect(ws_url, subprotocols=subprotocols) as ws:
        cfg = {
            "outputModalities": ["audio"],
            "instructions": "You are a clinic receptionist. When user asks for WhatsApp details, call send_whatsapp tool immediately. When user says bye, call end_call tool.",
            "voice": "Aoede"
        }
        if initial:
            cfg["tools"] = tools

        await ws.send(json.dumps({"type": "session-update", "config": cfg}))
        evt1 = json.loads(await ws.recv())
        print("Setup complete:", evt1.get("type"))

        if not initial:
            # Send tools in second update
            print("Sending tools in second update...")
            cfg["tools"] = tools
            await ws.send(json.dumps({"type": "session-update", "config": cfg}))
            await asyncio.sleep(0.5)

        # Trigger user request
        print("Sending user request: 'Please send WhatsApp details to 9876543210'...")
        await ws.send(json.dumps({
            "type": "conversation-item-create",
            "item": {"type": "text-message", "role": "user", "text": "Please send clinic details to my WhatsApp at 9876543210 right now."}
        }))

        # Listen for events
        func_called = False
        for _ in range(25):
            msg = await ws.recv()
            evt = json.loads(msg)
            ev_type = evt.get("type")
            if "function" in ev_type:
                print(f"*** TOOL CALL RECEIVED! *** -> {ev_type}: {evt}")
                func_called = True
                break
            elif ev_type in ("audio-done", "response-done"):
                print("Response finished.")
                break
        print(f"Tool call triggered? {func_called}")

async def main():
    await test_tools(initial=True)
    await test_tools(initial=False)

if __name__ == "__main__":
    asyncio.run(main())
