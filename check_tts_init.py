from run_ssh_cmd import run_ssh

code = """
import inspect
from pipecat.services.google.tts import GeminiTTSService

lines, _ = inspect.getsourcelines(GeminiTTSService.__init__)
for line in lines:
    print(line, end='')
"""

escaped = code.replace('"', '\\"').replace('$', '\\$')
run_ssh(f'sudo docker exec provaani_akruti-api-1 python -c "{escaped}"')
