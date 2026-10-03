from run_ssh_cmd import run_ssh

code = """
from api.schemas.ai_model_configuration import OrganizationAIModelConfigurationV2

cfg = {
    "byok": {
        "mode": "pipeline",
        "pipeline": {
            "llm": {
                "provider": "openrouter",
                "model": "openai/gpt-4o-mini",
                "base_url": "https://openrouter.ai/api/v1",
                "api_key": ["OPENROUTER_API_KEY_PLACEHOLDER"]
            },
            "stt": {
                "provider": "smallest",
                "model": "pulse",
                "language": "north_indic",
                "api_key": ["SMALLEST_AI_KEY_PLACEHOLDER"]
            },
            "tts": {
                "provider": "openai",
                "model": "google/gemini-3.8-flash-lite-tts",
                "base_url": "https://openrouter.ai/api/v1",
                "voice": "Aoede",
                "api_key": ["OPENROUTER_API_KEY_PLACEHOLDER"]
            }
        }
    },
    "mode": "byok",
    "version": 2
}

validated = OrganizationAIModelConfigurationV2(**cfg)
print("SUCCESSFULLY_VALIDATED_PYDANTIC:", validated.byok.pipeline.tts.provider, validated.byok.pipeline.tts.model, validated.byok.pipeline.tts.base_url)
"""

escaped = code.replace('"', '\\"').replace('$', '\\$')
run_ssh(f'sudo docker exec provaani_akruti-api-1 python -c "{escaped}"')
