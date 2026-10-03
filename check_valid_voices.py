from run_ssh_cmd import run_ssh

code = """
import inspect
import pipecat.services.openai.tts as otts
print("VALID_VOICES:", getattr(otts, 'VALID_VOICES', None))
"""

escaped = code.replace('"', '\\"').replace('$', '\\$')
run_ssh(f'sudo docker exec provaani_akruti-api-1 python -c "{escaped}"')
