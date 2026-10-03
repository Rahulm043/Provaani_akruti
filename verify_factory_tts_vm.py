import json
from run_ssh_cmd import run_ssh

code = """
import asyncio
import json
from pydantic import BaseModel
from api.services.pipecat.service_factory import create_tts_service
from api.db import db_client
from sqlalchemy import text

class DummyAudioConfig:
    pipeline_sample_rate = 24000
    transport_out_sample_rate = 8000

class DummyTTS(BaseModel):
    provider: str
    model: str
    voice: str
    language: str
    speed: float = 1.0
    api_key: list[str] | str | None = None

class DummyUserConfig(BaseModel):
    tts: DummyTTS

async def test():
    async with db_client.async_session() as session:
        res = await session.execute(text("SELECT workflow_configurations FROM workflows WHERE id = 4;"))
        row = res.first()
        cfg = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        tts_cfg = cfg["model_configuration_v2_override"]["byok"]["pipeline"]["tts"]
        print("Current DB WF4 TTS config:", tts_cfg)

        user_cfg = DummyUserConfig(tts=DummyTTS(**tts_cfg))
        audio_cfg = DummyAudioConfig()
        svc = create_tts_service(user_cfg, audio_cfg)
        print("Instantiated TTS Service successfully:", type(svc).__name__)
        print("Voice:", svc._settings.voice, "Model:", svc._settings.model, "Language:", svc._settings.language)

if __name__ == '__main__':
    asyncio.run(test())
"""

escaped = code.replace('"', '\\"').replace('$', '\\$')
run_ssh(f'sudo docker exec provaani_akruti-api-1 python -c "{escaped}"')
