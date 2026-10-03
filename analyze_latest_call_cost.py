import os
import requests
import json
from run_ssh_cmd import run_ssh

code = """
import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def main():
    async with db_client.async_session() as session:
        res = await session.execute(text("SELECT id, workflow_id, state, created_at, duration, user_turn_count, bot_turn_count, transcript, conversation_metrics FROM workflow_runs ORDER BY id DESC LIMIT 2;"))
        rows = res.fetchall()
        for r in rows:
            print(f"=== RUN ID: {r.id} | WF: {r.workflow_id} | State: {r.state} | Created: {r.created_at} ===")
            print(f"Duration: {r.duration}s | User Turns: {r.user_turn_count} | Bot Turns: {r.bot_turn_count}")
            if r.conversation_metrics:
                print("Metrics:", json.dumps(r.conversation_metrics, indent=2))
            if r.transcript:
                print("Transcript:", json.dumps(r.transcript, indent=2, ensure_ascii=False))
            print("=" * 60)

if __name__ == '__main__':
    asyncio.run(main())
"""

escaped = code.replace('"', '\\"').replace('$', '\\$')
run_ssh(f'sudo docker exec provaani_akruti-api-1 python -c "{escaped}"')
