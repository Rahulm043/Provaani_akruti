import asyncio
from api.services.pipecat.realtime.gemini_live import DograhGeminiLiveLLMService

async def test(model):
    api_key = "GOOGLE_AI_STUDIO_KEY_PLACEHOLDER"
    service = DograhGeminiLiveLLMService(
        api_key=api_key,
        settings=DograhGeminiLiveLLMService.Settings(
            model=model,
            voice="Aoede",
            system_instruction="Hello"
        )
    )
    try:
        # We start the session directly using service._client.aio.live.connect
        # to test if bidiGenerateContent accepts this model
        from google.genai.types import LiveConnectConfig, SpeechConfig, VoiceConfig, PrebuiltVoiceConfig
        config = LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=SpeechConfig(
                voice_config=VoiceConfig(
                    prebuilt_voice_config=PrebuiltVoiceConfig(voice_name="Aoede")
                )
            )
        )
        async with service._client.aio.live.connect(model=model, config=config) as session:
            print(f"[SUCCESS] '{model}' supports bidiGenerateContent!")
            return True
    except Exception as e:
        print(f"[FAIL] '{model}': {e}")
        return False

async def main():
    models = [
        "gemini-2.0-flash-exp",
        "gemini-2.0-flash-realtime-exp",
        "gemini-3.1-flash-live-preview",
        "gemini-2.5-flash-native-audio-preview",
        "models/gemini-2.0-flash-exp"
    ]
    for m in models:
        await test(m)

if __name__ == "__main__":
    asyncio.run(main())
