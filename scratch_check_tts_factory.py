from run_ssh_cmd import run_ssh

cmd = """sudo docker exec provaani_akruti-api-1 python -c "
import inspect
import api.services.pipecat.service_factory as sf
lines, _ = inspect.getsourcelines(sf.create_tts_service)
for i, line in enumerate(lines[:65]):
    print(f'{i+1}: {line}', end='')
"
"""
run_ssh(cmd)
