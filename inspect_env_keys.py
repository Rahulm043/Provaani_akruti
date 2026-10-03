from run_ssh_cmd import run_ssh

code = """
import os
for k, v in os.environ.items():
    if any(x in k.lower() for x in ['key', 'secret', 'token', 'google', 'gemini', 'vercel', 'cerebras', 'smallest']):
        masked = v[:8] + '...' if len(v) > 8 else '***'
        print(f'{k}: {masked}')
"""

escaped = code.replace('"', '\\"').replace('$', '\\$')
run_ssh(f'sudo docker exec provaani_akruti-api-1 python -c "{escaped}"')
