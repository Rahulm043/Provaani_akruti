import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

py_code = """
import os, asyncio
from pipecat.services.google.tts import GeminiTTSService, GeminiTTSSettings

key = os.getenv('Google_ai_studio') or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY') or 'GOOGLE_AI_STUDIO_KEY_PLACEHOLDER'

try:
    svc = GeminiTTSService(
        api_key=key,
        model='gemini-3.8-flash-lite-tts',
        voice_id='Aoede',
        use_genai=True,
        settings=GeminiTTSSettings(
            model='gemini-3.8-flash-lite-tts',
            voice='Aoede'
        )
    )
    print("SUCCESS_GEMINI_TTS_INSTANTIATE:", type(svc))
except Exception as e:
    import traceback
    traceback.print_exc()
"""

cmd = [
    "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
    "-o", "StrictHostKeyChecking=no",
    "rahul@34.131.238.156",
    "sudo docker exec -i provaani_akruti-api-1 python"
]

proc = subprocess.run(cmd, input=py_code, capture_output=True, text=True, errors="replace")
print("stdout:\n", proc.stdout)
print("stderr:\n", proc.stderr)
