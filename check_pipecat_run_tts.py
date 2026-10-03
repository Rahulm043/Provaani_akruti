from run_ssh_cmd import run_ssh

code = """
import inspect
from pipecat.services.openai.tts import OpenAITTSService

lines, _ = inspect.getsourcelines(OpenAITTSService.run_tts)
for i, l in enumerate(lines):
    print(f'{i+1}: {l}', end='')
"""

escaped = code.replace('"', '\\"').replace('$', '\\$')
run_ssh(f'sudo docker exec provaani_akruti-api-1 python -c "{escaped}"')
