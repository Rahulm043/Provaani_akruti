from run_ssh_cmd import run_ssh

code = """
import inspect
from pipecat.services.openai.tts import OpenAITTSService, OpenAITTSSettings
print("OpenAITTSSettings annotations:", getattr(OpenAITTSSettings, '__annotations__', {}))
lines, _ = inspect.getsourcelines(OpenAITTSService.run_tts)
for l in lines[:40]:
    print(l, end='')
"""

escaped = code.replace('"', '\\"').replace('$', '\\$')
run_ssh(f'sudo docker exec provaani_akruti-api-1 python -c "{escaped}"')
