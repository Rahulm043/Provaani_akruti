import asyncio
from api.services.pipecat.realtime.gemini_live import DograhGeminiLiveLLMService

async def test_model(model_name):
    api_key = "GOOGLE_AI_STUDIO_KEY_PLACEHOLDER"
    print(f"\n--- Testing model: '{model_name}' ---")
    service = DograhGeminiLiveLLMService(
        api_key=api_key,
        settings=DograhGeminiLiveLLMService.Settings(
            model=model_name,
            voice="Aoede",
            system_instruction="You are Akruti."
        )
    )
    try:
        await service._connect()
        print(f"[SUCCESS] Model '{model_name}' connected successfully!")
        await service._disconnect()
        return True
    except Exception as e:
        print(f"[FAILED] Model '{model_name}': {e}")
        return False

async def main():
    models_to_test = [
        "gemini-3.8-flash",
        "gemini-3.8-live",
        "gemini-3.8-flash-live",
        "gemini-3.1-flash-live-preview",
        "models/gemini-3.8-flash"
    ]
    for m in models_to_test:
        await test_model(m)

if __name__ == "__main__":
    asyncio.run(main())
