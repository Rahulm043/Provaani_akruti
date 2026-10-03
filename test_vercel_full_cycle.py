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
        
        # 1. Send session-update
        session_update = {
            "type": "session-update",
            "config": {
                "outputModalities": ["audio"],
                "instructions": "You are Akruti Aesthetics receptionist in Kolkata. Speak in Bengali.",
                "voice": "Aoede"
            }
        }
        await ws.send(json.dumps(session_update))
        print("Sent session-update")

        # 2. Wait for session-created
        while True:
            msg = await ws.recv()
            evt = json.loads(msg)
            print("Setup event:", evt.get("type"))
            if evt.get("type") == "session-created":
                print("Session is ready!")
                break

        # 3. Send Bengali greeting prompt as conversation-item-create (WITHOUT response-create!)
        greeting_text = "নমস্কার! আকৃতি এস্থেটিক্স ক্লিনিকে আপনাকে স্বাগতম। আমি কীভাবে আপনাকে সাহায্য করতে পারি?"
        prompt = f"Please speak out this exact Bengali greeting warmly to the caller: '{greeting_text}'"
        item = {
            "type": "conversation-item-create",
            "item": {
                "type": "text-message",
                "role": "user",
                "text": prompt
            }
        }
        await ws.send(json.dumps(item))
        print("Sent Bengali greeting prompt!")

        # 4. Receive audio and transcript
        total_audio = 0
        transcript = ""
        while True:
            msg = await ws.recv()
            evt = json.loads(msg)
            ev_type = evt.get("type")
            if ev_type == "audio-delta":
                chunk = base64.b64decode(evt.get("delta", ""))
                total_audio += len(chunk)
            elif ev_type == "audio-transcript-delta":
                transcript += evt.get("delta", "")
            elif ev_type == "audio-done":
                usage = evt.get("raw", {}).get("usageMetadata", {})
                print(f"\nAudio Done! Received {total_audio} bytes audio.")
                print(f"Transcript: {transcript}")
                print(f"Usage: {usage}")
                break

if __name__ == "__main__":
    asyncio.run(test())
