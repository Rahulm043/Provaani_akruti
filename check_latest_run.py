import asyncio
from api.db import db_client
from sqlalchemy import text

async def check():
    async with db_client.async_session() as session:
        res = await session.execute(text("""
            SELECT id, workflow_id, state, created_at, updated_at
            FROM workflow_runs
            ORDER BY id DESC
            LIMIT 5;
        """))
        for row in res.fetchall():
            print(f"Run {row[0]}: wf={row[1]}, state={row[2]}, created={row[3]}, updated={row[4]}")

if __name__ == "__main__":
    asyncio.run(check())
