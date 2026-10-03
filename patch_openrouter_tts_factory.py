from run_ssh_cmd import run_ssh

code = """
import re

file_path = "/app/api/services/pipecat/service_factory.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

target = '''    elif user_config.tts.provider == ServiceProviders.OPENAI.value:
        kwargs = {}
        base_url = getattr(user_config.tts, "base_url", None)
        if base_url:
            _validate_runtime_service_url(base_url, "base_url")
            kwargs["base_url"] = base_url
        return OpenAITTSService(
            api_key=user_config.tts.api_key,
            sample_rate=OPENAI_SAMPLE_RATE,
            settings=OpenAITTSSettings(model=user_config.tts.model),
            text_filters=[xml_function_tag_filter],
            skip_aggregator_types=["recording_router", "recording"],
            silence_time_s=1.0,
            **kwargs,
        )'''

replacement = '''    elif user_config.tts.provider in (ServiceProviders.OPENAI.value, "openrouter"):
        kwargs = {}
        base_url = getattr(user_config.tts, "base_url", None) or ("https://openrouter.ai/api/v1" if user_config.tts.provider == "openrouter" or "openrouter" in str(getattr(user_config.tts, "model", "")).lower() or "gemini" in str(getattr(user_config.tts, "model", "")).lower() else None)
        if base_url:
            _validate_runtime_service_url(base_url, "base_url")
            kwargs["base_url"] = base_url
        
        voice = getattr(user_config.tts, "voice", None) or "Aoede"
        from pipecat.services.openai.tts import VALID_VOICES
        if voice not in VALID_VOICES:
            VALID_VOICES[voice] = voice
            VALID_VOICES[voice.lower()] = voice
        for gv in ["Aoede", "Kore", "Puck", "Charon", "Fenrir", "Leda", "Zephyr", "Orus"]:
            VALID_VOICES[gv] = gv
            VALID_VOICES[gv.lower()] = gv

        api_key = getattr(user_config.tts, "api_key", None)
        if isinstance(api_key, list):
            api_key = api_key[0] if api_key else None
        if not api_key:
            api_key = os.environ.get("OPENROUTER_API_KEY") if "openrouter" in (base_url or "") else os.environ.get("OPENAI_API_KEY")

        return OpenAITTSService(
            api_key=api_key,
            sample_rate=24000 if ("openrouter" in (base_url or "") or "gemini" in str(getattr(user_config.tts, "model", "")).lower()) else OPENAI_SAMPLE_RATE,
            settings=OpenAITTSSettings(model=user_config.tts.model, voice=voice),
            text_filters=[xml_function_tag_filter],
            skip_aggregator_types=["recording_router", "recording"],
            silence_time_s=1.0,
            **kwargs,
        )'''

if target in content:
    content = content.replace(target, replacement, 1)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("PATCH_APPLIED_SUCCESSFULLY")
else:
    print("TARGET_NOT_FOUND")
"""

escaped = code.replace('"', '\\"').replace('$', '\\$')
run_ssh(f'sudo docker exec -u 0 provaani_akruti-api-1 python -c "{escaped}"')
