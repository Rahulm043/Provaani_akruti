import json
from run_ssh_cmd import run_ssh

code = """
import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def main():
    async with db_client.async_session() as session:
        res = await session.execute(text("SELECT * FROM workflow_runs ORDER BY id DESC LIMIT 2;"))
        for row in res.mappings():
            d = dict(row)
            print(f"=== RUN ID: {d.get('id')} | State: {d.get('state')} ===")
            for k, v in d.items():
                if k not in ['public_access_token', 'run_data']:
                    print(f"{k}: {v}")
            print("-" * 50)

if __name__ == '__main__':
    asyncio.run(main())
"""

escaped = code.replace('"', '\\"').replace('$', '\\$')
run_ssh(f'sudo docker exec provaani_akruti-api-1 python -c "{escaped}"')
