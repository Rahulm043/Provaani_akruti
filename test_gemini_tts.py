import asyncio
from pipecat.services.google.tts import GeminiTTSService

async def test():
    tts = GeminiTTSService(
        api_key="GOOGLE_AI_STUDIO_KEY_PLACEHOLDER",
        sample_rate=24000,
        settings=GeminiTTSService.Settings(
            model="gemini-3.8-flash-lite-tts",
            voice="Aoede",
        ),
    )
    # Crucial: in standalone usage without a Pipeline, _sample_rate must be explicitly initialized
    tts._sample_rate = 24000
    print("chunk_size:", tts.chunk_size, flush=True)

    frames = []
    print("Starting run_tts...", flush=True)
    async for frame in tts.run_tts("Hello, testing Gemini 3.8 flash lite speech synthesis.", context_id="test-1"):
        frames.append(frame)
        audio_len = len(getattr(frame, "audio", b""))
        print(f"Frame {len(frames)}: {type(frame).__name__}, audio bytes: {audio_len}", flush=True)
    print(f"Total frames received: {len(frames)}", flush=True)

if __name__ == "__main__":
    asyncio.run(test())
