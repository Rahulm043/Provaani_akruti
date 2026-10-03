from run_ssh_cmd import run_ssh

code = """
import inspect
from api.services.pipecat.service_factory import create_llm_service_from_provider

lines, _ = inspect.getsourcelines(create_llm_service_from_provider)
for i, l in enumerate(lines):
    if any(k in l.lower() for k in ['cerebras', 'openai', 'provider']):
        print(f'{i+1}: {l}', end='')
"""

escaped = code.replace('"', '\\"').replace('$', '\\$')
run_ssh(f'sudo docker exec provaani_akruti-api-1 python -c "{escaped}"')
