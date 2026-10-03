import asyncio
import base64
import json
import requests
import websockets
from loguru import logger

class VercelRealtimeSession:
    def __init__(self, api_key: str, model: str = "google/gemini-3.8-live", voice: str = "Aoede", instructions: str = ""):
        self.api_key = api_key
        self.model = model
        self.voice = voice
        self.instructions = instructions
        self.ws = None
        self.connected = False
        self._recv_task = None
        self.on_audio_delta = None
        self.on_transcript_delta = None
        self.on_usage = None

    def mint_token(self) -> str:
        url = "https://ai-gateway.vercel.sh/v1/realtime/client-secrets"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        resp = requests.post(url, headers=headers, json={"model": self.model}, timeout=10)
        resp.raise_for_status()
        return resp.json()["token"]

    async def connect(self):
        token = await asyncio.to_thread(self.mint_token)
        ws_url = f"wss://ai-gateway.vercel.sh/v4/ai/realtime-model?ai-model-id={self.model.replace('/', '%2F')}"
        subprotocols = ["ai-gateway-realtime.v1", f"ai-gateway-auth.{token}"]
        logger.info(f"Connecting to Vercel AI Gateway: {ws_url}")
        
        self.ws = await websockets.connect(ws_url, subprotocols=subprotocols)
        self.connected = True
        logger.info("Connected to Vercel AI Gateway WebSocket!")

        # Send session-update
        session_event = {
            "type": "session-update",
            "config": {
                "outputModalities": ["audio"],
                "instructions": self.instructions,
                "voice": self.voice
            }
        }
        await self.ws.send(json.dumps(session_event))
        logger.info("Sent session-update to Vercel AI Gateway")
        self._recv_task = asyncio.create_task(self._receive_loop())

    async def send_audio(self, pcm_bytes: bytes):
        if not self.ws or not self.connected:
            return
        b64_audio = base64.b64encode(pcm_bytes).decode("ascii")
        event = {
            "type": "input-audio-append",
            "audio": b64_audio
        }
        await self.ws.send(json.dumps(event))

    async def trigger_greeting(self, text: str):
        if not self.ws or not self.connected:
            return
        event = {
            "type": "conversation-item-create",
            "item": {
                "type": "text-message",
                "role": "user",
                "text": f"Please say this exact opening greeting now in a warm tone: '{text}'"
            }
        }
        await self.ws.send(json.dumps(event))
        await self.ws.send(json.dumps({"type": "response-create"}))
        logger.info(f"Triggered opening greeting via Vercel AI Gateway: {text}")

    async def _receive_loop(self):
        try:
            while self.connected:
                msg = await self.ws.recv()
                event = json.loads(msg)
                ev_type = event.get("type")
                if ev_type == "audio-delta":
                    delta_b64 = event.get("delta", "")
                    if delta_b64 and self.on_audio_delta:
                        pcm = base64.b64decode(delta_b64)
                        self.on_audio_delta(pcm)
                elif ev_type == "audio-transcript-delta":
                    delta_text = event.get("delta", "")
                    if delta_text and self.on_transcript_delta:
                        self.on_transcript_delta(delta_text)
                elif ev_type == "response-done":
                    raw = event.get("raw", {})
                    usage = raw.get("usageMetadata")
                    logger.info(f"Response done. Usage: {usage}")
                    if self.on_usage:
                        self.on_usage(usage)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in Vercel receive loop: {e}")

    async def close(self):
        self.connected = False
        if self._recv_task:
            self._recv_task.cancel()
        if self.ws:
            await self.ws.close()

async def main():
    api_key = "VERCEL_AI_KEY_PLACEHOLDER"
    session = VercelRealtimeSession(
        api_key=api_key,
        model="google/gemini-3.8-live",
        voice="Aoede",
        instructions="You are Akruti Aesthetics Clinic assistant. Speak warmly."
    )

    audio_received = []
    transcripts = []

    session.on_audio_delta = lambda pcm: audio_received.append(len(pcm))
    session.on_transcript_delta = lambda text: transcripts.append(text)

    await session.connect()
    await session.trigger_greeting("নমস্কার! আকৃতি নান্দনিক ও প্লাস্টিক সার্জারি ক্লিনিকে আপনাকে স্বাগত। বলুন, আপনাকে কীভাবে সাহায্য করতে পারি?")
    
    # Wait for response audio
    await asyncio.sleep(6)
    await session.close()

    print("\n--- TEST SUMMARY ---")
    print(f"Total audio chunks: {len(audio_received)} (total bytes: {sum(audio_received)})")
    print(f"Transcript: {''.join(transcripts)}")
    print("--------------------")

if __name__ == "__main__":
    asyncio.run(main())
