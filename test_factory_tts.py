import asyncio
from pydantic import BaseModel
from typing import Any
from api.services.pipecat.service_factory import create_tts_service
from pipecat.audio.vad.vad_analyzer import VADParams

class DummyAudioConfig:
    pipeline_sample_rate = 24000
    transport_out_sample_rate = 8000

class DummyTTS(BaseModel):
    provider: str = "google"
    model: str = "gemini-3.8-flash-lite-tts"
    voice: str = "Aoede"
    language: str = "en-US"
    speed: float = 1.0
    api_key: list[str] | str | None = ["GOOGLE_AI_STUDIO_KEY_PLACEHOLDER"]

class DummyUserConfig(BaseModel):
    tts: DummyTTS

def test():
    user_config = DummyUserConfig(tts=DummyTTS())
    audio_config = DummyAudioConfig()
    tts_service = create_tts_service(user_config, audio_config)
    print("Successfully created TTS service:", type(tts_service).__name__, tts_service)
    print("tts_service._use_genai:", getattr(tts_service, "_use_genai", None))
    print("tts_service._settings:", getattr(tts_service, "_settings", None))

if __name__ == "__main__":
    test()
