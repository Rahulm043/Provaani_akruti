import asyncio
import json
import requests
import websockets

async def test_tools_update():
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
            "description": "End the call gracefully",
            "parameters": {"type": "object", "properties": {}}
        }
    ]

    async with websockets.connect(ws_url, subprotocols=subprotocols) as ws:
        # Case A: First session-update WITHOUT tools
        print("Sending initial session-update WITHOUT tools...")
        await ws.send(json.dumps({
            "type": "session-update",
            "config": {"outputModalities": ["audio"], "instructions": "You are a receptionist.", "voice": "Aoede"}
        }))
        evt1 = json.loads(await ws.recv())
        print("First session-update result:", evt1.get("type"))

        # Case B: Second session-update WITH tools
        print("Sending second session-update WITH tools...")
        await ws.send(json.dumps({
            "type": "session-update",
            "config": {
                "outputModalities": ["audio"],
                "instructions": "You are a receptionist.",
                "voice": "Aoede",
                "tools": tools
            }
        }))
        
        try:
            msg = await asyncio.wait_for(ws.recv(), timeout=4.0)
            print("Received after second session-update:", msg[:200])
        except Exception as e:
            print("Failed or timed out on second session-update:", e)

if __name__ == "__main__":
    asyncio.run(test_tools_update())
