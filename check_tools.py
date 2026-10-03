import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def check():
    async with db_client.async_session() as session:
        for wf_id in [1, 4]:
            res = await session.execute(text(f"SELECT id, name, workflow_definition FROM workflows WHERE id = {wf_id};"))
            row = res.first()
            wf = row[2] if isinstance(row[2], dict) else json.loads(row[2])
            tools = wf.get("tools", [])
            print(f"\nWF {row[0]} ({row[1]}):")
            print(f"Total tools: {len(tools)}")
            for t in tools:
                print(f"  Tool: {t.get('name')} (id: {t.get('id')})")
                print(f"    params: {list(t.get('parameters', {}).get('properties', {}).keys())}")

if __name__ == "__main__":
    asyncio.run(check())
