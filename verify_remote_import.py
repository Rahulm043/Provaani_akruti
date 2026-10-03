import subprocess

cmd = [
    "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
    "-o", "StrictHostKeyChecking=no",
    "rahul@34.131.238.156",
    "sudo docker cp /tmp/vercel_realtime.py provaani_akruti-api-1:/app/api/services/pipecat/realtime/vercel_realtime.py && sudo docker exec provaani_akruti-api-1 python3 -c 'from api.services.pipecat.realtime.vercel_realtime import DograhVercelRealtimeLLMService; s = DograhVercelRealtimeLLMService.Settings(model=\"google/gemini-3.8-live\", voice=\"Aoede\", language=\"bn\"); svc = DograhVercelRealtimeLLMService(api_key=\"VERCEL_AI_KEY_PLACEHOLDER\", settings=s); print(\"SUCCESSFULLY INSTANTIATED SERVICE! model=\", svc._model, \"voice=\", svc._voice)'"
]
proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace")
print("STDOUT:", proc.stdout.encode("ascii", "replace").decode("ascii"))
print("STDERR:", proc.stderr.encode("ascii", "replace").decode("ascii"))
