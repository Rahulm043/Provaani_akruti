import asyncio
from api.services.pipecat.realtime.gemini_live import DograhGeminiLiveLLMService

async def test():
    api_key = "GOOGLE_AI_STUDIO_KEY_PLACEHOLDER"
    print("Testing DograhGeminiLiveLLMService connection with Google AI Studio key...")
    service = DograhGeminiLiveLLMService(
        api_key=api_key,
        settings=DograhGeminiLiveLLMService.Settings(
            model="gemini-2.0-flash-exp",
            voice="Aoede",
            system_instruction="You are Akruti from Provaani."
        )
    )
    try:
        await service._connect()
        print("[SUCCESS] Gemini Live connected successfully!")
        await service._disconnect()
    except Exception as e:
        print("[ERROR] Failed to connect:", type(e), e)

if __name__ == "__main__":
    asyncio.run(test())
