from run_ssh_cmd import run_ssh

code = """
import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def main():
    async with db_client.async_session() as session:
        res = await session.execute(text("SELECT id, name, workflow_id, created_at, usage_info, logs FROM workflow_runs WHERE id = 248;"))
        r = res.mappings().first()
        if r:
            print(f"Run ID: {r['id']} | Created: {r['created_at']}")
            print("Usage Info:", json.dumps(r['usage_info'], indent=2))
            if r['logs']:
                print("Logs Realtime Feedback Events:")
                for e in r['logs'].get('realtime_feedback_events', []):
                    print(f"  [{e.get('type')}] turn={e.get('turn')} | {e.get('payload')}")

if __name__ == '__main__':
    asyncio.run(main())
"""

escaped = code.replace('"', '\\"').replace('$', '\\$')
run_ssh(f'sudo docker exec provaani_akruti-api-1 python -c "{escaped}"')
