import asyncio
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("OPENROUTER_API_KEY", "OPENROUTER_API_KEY_PLACEHOLDER")

async def main():
    client = AsyncOpenAI(
        api_key=key,
        base_url="https://openrouter.ai/api/v1"
    )
    print("Testing OpenAI AsyncClient against OpenRouter audio.speech...")
    try:
        async with client.audio.speech.with_streaming_response.create(
            model="google/gemini-3.8-flash-lite-tts",
            voice="Aoede",
            input="নমস্কার! আকৃতি নান্দনিক ও প্লাস্টিক সার্জারি ক্লিনিকে আপনাকে স্বাগত।",
            response_format="pcm"
        ) as response:
            print("Response status:", response.status_code)
            total = 0
            async for chunk in response.iter_bytes():
                total += len(chunk)
            print(f"Success! Read {total} bytes from stream.")
    except Exception as e:
        print("Error from AsyncOpenAI client:", type(e), e)

if __name__ == "__main__":
    asyncio.run(main())
