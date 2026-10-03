import asyncio
import os
import sys
import traceback
from loguru import logger
logger.remove()
logger.add(sys.stdout, level="DEBUG")
from api.services.pipecat.realtime.gemini_live import DograhGeminiLiveLLMService

async def test():
    api_key = "GOOGLE_AI_STUDIO_KEY_PLACEHOLDER"
    for model_candidate in ["models/gemini-3.8-live", "gemini-3.8-live"]:
        print(f"\n==========================================")
        print(f"Testing DograhGeminiLiveLLMService with model={model_candidate}")
        try:
            service = DograhGeminiLiveLLMService(
                api_key=api_key,
                settings=DograhGeminiLiveLLMService.Settings(
                    model=model_candidate,
                    voice="Aoede",
                    system_instruction="You are a helpful assistant.",
                )
            )
            print(f"Service instantiated. _is_gemini_3 = {service._is_gemini_3}")
            # Try to connect
            await service._connect(session_resumption_handle=None)
            print("Awaiting session ready...")
            # Wait up to 5 seconds for connection
            for _ in range(50):
                if service._session is not None:
                    break
                await asyncio.sleep(0.1)
            
            if service._session is not None:
                print(f"[SUCCESS] DograhGeminiLiveLLMService successfully connected with {model_candidate}!")
                await service._disconnect()
                return model_candidate
            else:
                print(f"[FAIL] Session was not established for {model_candidate}")
        except Exception as e:
            print(f"[EXCEPTION] Failed for {model_candidate}: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
