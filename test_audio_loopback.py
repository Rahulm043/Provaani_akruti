import asyncio
import base64
import json
import requests
import websockets

async def get_test_speech():
    url = "https://ai-gateway.vercel.sh/v1/realtime/client-secrets"
    headers = {"Authorization": "Bearer VERCEL_AI_KEY_PLACEHOLDER", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json={"model": "google/gemini-3.8-live"})
    token = resp.json()["token"]
    ws_url = "wss://ai-gateway.vercel.sh/v4/ai/realtime-model?ai-model-id=google%2Fgemini-3.8-live"
    subprotocols = ["ai-gateway-realtime.v1", f"ai-gateway-auth.{token}"]
    
    audio_chunks = []
    async with websockets.connect(ws_url, subprotocols=subprotocols) as ws:
        await ws.send(json.dumps({
            "type": "session-update",
            "config": {"outputModalities": ["audio"], "instructions": "Repeat exactly what is asked.", "voice": "Aoede"}
        }))
        while True:
            evt = json.loads(await ws.recv())
            if evt.get("type") == "session-created":
                break
        
        await ws.send(json.dumps({
            "type": "conversation-item-create",
            "item": {"type": "text-message", "role": "user", "text": "Please say: 'What time does the clinic open tomorrow?'"}
        }))
        
        while True:
            evt = json.loads(await ws.recv())
            if evt.get("type") == "audio-delta":
                audio_chunks.append(base64.b64decode(evt.get("delta", "")))
            elif evt.get("type") in ("audio-done", "response-done"):
                break
    return b"".join(audio_chunks)

async def test_input_audio(pcm_audio):
    from pipecat.audio.utils import create_stream_resampler
    resampler = create_stream_resampler()
    # Resample 24k -> 16k
    pcm_audio_16k = await resampler.resample(pcm_audio, 24000, 16000)
    print(f"Resampled to 16kHz: {len(pcm_audio_16k)} bytes. Testing input audio with 16kHz...")
    url = "https://ai-gateway.vercel.sh/v1/realtime/client-secrets"
    headers = {"Authorization": "Bearer VERCEL_AI_KEY_PLACEHOLDER", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json={"model": "google/gemini-3.8-live"})
    token = resp.json()["token"]
    ws_url = "wss://ai-gateway.vercel.sh/v4/ai/realtime-model?ai-model-id=google%2Fgemini-3.8-live"
    subprotocols = ["ai-gateway-realtime.v1", f"ai-gateway-auth.{token}"]

    async with websockets.connect(ws_url, subprotocols=subprotocols) as ws:
        await ws.send(json.dumps({
            "type": "session-update",
            "config": {"outputModalities": ["audio"], "instructions": "You are a clinic assistant. Answer questions concisely.", "voice": "Aoede"}
        }))
        while True:
            evt = json.loads(await ws.recv())
            if evt.get("type") == "session-created":
                break
        
        chunk_size = 1600 # 50ms at 16kHz 16-bit
        for i in range(0, len(pcm_audio_16k), chunk_size):
            chunk = pcm_audio_16k[i:i+chunk_size]
            await ws.send(json.dumps({
                "type": "input-audio-append",
                "audio": base64.b64encode(chunk).decode("ascii")
            }))
            await asyncio.sleep(0.02)
        
        # Send trailing silence (1.5s of zeros at 16kHz)
        silence = b"\x00" * int(16000 * 2 * 1.5)
        for i in range(0, len(silence), chunk_size):
            chunk = silence[i:i+chunk_size]
            await ws.send(json.dumps({
                "type": "input-audio-append",
                "audio": base64.b64encode(chunk).decode("ascii")
            }))
            await asyncio.sleep(0.02)
        
        print("Finished sending 16kHz audio chunks. Sending input-audio-commit...")
        await ws.send(json.dumps({"type": "input-audio-commit"}))
        
        print("Waiting for Gemini response...")
        received_audio = 0
        transcript = ""
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=6.0)
                evt = json.loads(msg)
                ev_type = evt.get("type")
                if ev_type == "audio-delta":
                    received_audio += len(base64.b64decode(evt.get("delta", "")))
                elif ev_type == "audio-transcript-delta":
                    transcript += evt.get("delta", "")
                elif ev_type in ("audio-done", "response-done"):
                    print(f"SUCCESS! Gemini responded to audio: {received_audio} bytes audio. Transcript: {transcript}")
                    break
                elif ev_type == "input-transcription-completed":
                    print(f"User speech transcribed: {evt.get('transcript')}")
                else:
                    print("Received other event:", ev_type, json.dumps(evt)[:200])
            except asyncio.TimeoutError:
                print("Timeout waiting for response to audio")
                break

async def main():
    speech = await get_test_speech()
    await test_input_audio(speech)

if __name__ == "__main__":
    asyncio.run(main())
