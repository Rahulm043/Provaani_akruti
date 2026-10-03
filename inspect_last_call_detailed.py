from run_ssh_cmd import run_ssh

code = """
import asyncio
from api.db import db_client
from sqlalchemy import text
import json

async def main():
    async with db_client.async_session() as session:
        res = await session.execute(text("SELECT id, workflow_id, status, created_at, updated_at, transcript FROM runs ORDER BY id DESC LIMIT 3;"))
        rows = res.fetchall()
        for r in rows:
            print(f"Run ID: {r.id} | WF: {r.workflow_id} | Status: {r.status} | Created: {r.created_at} | Updated: {r.updated_at}")
            if r.transcript:
                print("Transcript:", json.dumps(r.transcript, indent=2, ensure_ascii=False))
            print("-" * 50)

if __name__ == '__main__':
    asyncio.run(main())
"""

escaped = code.replace('"', '\\"').replace('$', '\\$')
run_ssh(f'sudo docker exec provaani_akruti-api-1 python -c "{escaped}"')
