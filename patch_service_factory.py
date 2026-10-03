with open("/tmp/service_factory.py", "r", encoding="utf-8") as f:
    content = f.read()

target = '''    elif provider == ServiceProviders.GOOGLE_REALTIME.value:
        if api_key and (api_key.startswith("vck_") or "vercel" in (model or "").lower()):
            from api.services.pipecat.realtime.vercel_realtime import (
                DograhVercelRealtimeLLMService,
            )
            settings_kwargs = {
                "model": model if "/" in (model or "") else f"google/{model}",
                "voice": voice or "Aoede",
            }
            if language:
                settings_kwargs["language"] = language
            return DograhVercelRealtimeLLMService(
                api_key=api_key,
                settings=DograhVercelRealtimeLLMService.Settings(**settings_kwargs),
            )'''

replacement = '''    elif provider == ServiceProviders.GOOGLE_REALTIME.value:
        actual_key = api_key[0] if isinstance(api_key, list) else api_key
        if actual_key and (str(actual_key).startswith("vck_") or "vercel" in (model or "").lower()):
            from api.services.pipecat.realtime.vercel_realtime import (
                DograhVercelRealtimeLLMService,
            )
            settings_kwargs = {
                "model": model if "/" in (model or "") else f"google/{model}",
                "voice": voice or "Aoede",
            }
            if language:
                settings_kwargs["language"] = language
            return DograhVercelRealtimeLLMService(
                api_key=str(actual_key),
                settings=DograhVercelRealtimeLLMService.Settings(**settings_kwargs),
            )'''

if target in content:
    content = content.replace(target, replacement, 1)
    with open("/tmp/service_factory.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("PATCH_APPLIED_SUCCESSFULLY")
else:
    print("TARGET_NOT_FOUND")
