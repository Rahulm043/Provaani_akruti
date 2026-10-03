import subprocess

cmd = [
    "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
    "-o", "StrictHostKeyChecking=no",
    "rahul@34.131.238.156",
    """sudo docker exec provaani_akruti-api-1 python3 -c "
from api.services.pipecat.service_factory import create_realtime_llm_service

class DummyRealtime:
    provider = 'google_realtime'
    model = 'google/gemini-3.8-live'
    api_key = 'VERCEL_AI_KEY_PLACEHOLDER'
    voice = 'Aoede'
    language = 'bn'

class DummyUserConfig:
    realtime = DummyRealtime()

svc = create_realtime_llm_service(
    user_config=DummyUserConfig(),
    audio_config=None,
)
print('FACTORY DISPATCH SUCCESS:', type(svc).__name__, 'model:', svc.model_name, 'voice:', svc._voice)
" """
]
proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
print("STDOUT:", proc.stdout.encode("ascii", "replace").decode("ascii"))
print("STDERR:", proc.stderr.encode("ascii", "replace").decode("ascii"))
