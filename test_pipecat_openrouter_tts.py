import asyncio
import os
from dotenv import load_dotenv
from pipecat.services.openai.tts import OpenAITTSService, OpenAITTSSettings

load_dotenv()
key = os.getenv("OPENROUTER_API_KEY", "OPENROUTER_API_KEY_PLACEHOLDER")

async def test():
    tts = OpenAITTSService(
        api_key=key,
        base_url="https://openrouter.ai/api/v1",
        sample_rate=24000,
        settings=OpenAITTSSettings(
            model="google/gemini-3.8-flash-lite-tts",
            voice="Aoede",
            response_format="pcm",
        ),
    )
    tts._sample_rate = 24000
    print("Testing OpenAITTSService against OpenRouter Gemini 3.8 Flash-Lite TTS...")
    frames = []
    text = "নমস্কার! আকৃতি নান্দনিক ও প্লাস্টিক সার্জারি ক্লিনিকে আপনাকে স্বাগত।"
    async for frame in tts.run_tts(text, context_id="test-1"):
        frames.append(frame)
        audio_len = len(getattr(frame, "audio", b""))
        print(f"Frame {len(frames)}: {type(frame).__name__} ({audio_len} bytes)")
    print(f"DONE! Total frames: {len(frames)}")

if __name__ == "__main__":
    asyncio.run(test())
