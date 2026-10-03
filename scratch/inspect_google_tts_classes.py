import subprocess

py = """
import pipecat.services.google.tts as gtts
import inspect
for name, cls in inspect.getmembers(gtts, inspect.isclass):
    if "TTS" in name:
        print(name, inspect.signature(cls.__init__))
"""

cmd = [
    "ssh", "-i", r"C:\Users\rahul\.ssh\google_compute_engine",
    "-o", "StrictHostKeyChecking=no",
    "rahul@34.131.238.156",
    "sudo docker exec -i provaani_akruti-api-1 python"
]

proc = subprocess.run(cmd, input=py, capture_output=True, text=True, errors="replace")
print("stdout:\n", proc.stdout)
print("stderr:\n", proc.stderr)
