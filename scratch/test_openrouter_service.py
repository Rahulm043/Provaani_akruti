import subprocess
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

py_code = """
from api.services.pipecat.service_factory import create_llm_service_from_provider

try:
    llm_service = create_llm_service_from_provider(
        provider='openrouter',
        model='openai/gpt-4o-mini',
        api_key='OPENROUTER_API_KEY_PLACEHOLDER',
        temperature=0.1,
        base_url='https://openrouter.ai/api/v1'
    )
    print("SUCCESS_LLM_SERVICE:", type(llm_service))
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
