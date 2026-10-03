import asyncio
import os
from google import genai
from google.genai import types

API_KEY = "GOOGLE_AI_STUDIO_KEY_PLACEHOLDER"

async def test_live(model_name: str, voice_name: str = "Aoede"):
    print(f"\n--- Testing model: {model_name} with voice: {voice_name} ---")
    try:
        client = genai.Client(
            http_options={"api_version": "v1beta"},
            api_key=API_KEY,
        )
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
                )
            ),
        )
        async with client.aio.live.connect(model=model_name, config=config) as session:
            print(f"[SUCCESS] Connected to live session with model={model_name}!")
            # Send a quick text turn to see if it responds with audio
            await session.send(input="Hello, can you hear me?", end_of_turn=True)
            turn = session.receive()
            chunks_received = 0
            async for response in turn:
                if response.data:
                    chunks_received += 1
                    if chunks_received >= 3:
                        print(f"[SUCCESS] Received {chunks_received}+ audio chunks from {model_name}!")
                        break
                if response.text:
                    print(f"Text response: {response.text}")
            print(f"[VERIFIED] Live audio streaming works for {model_name}!")
            return True
    except Exception as e:
        print(f"[ERROR] Failed for {model_name}: {e}")
        return False

async def main():
    models_to_test = [
        "models/gemini-3.8-live",
        "gemini-3.8-live",
        "models/gemini-2.0-flash-exp",
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash-realtime-exp",
    ]
    for m in models_to_test:
        await test_live(m)

if __name__ == "__main__":
    asyncio.run(main())
