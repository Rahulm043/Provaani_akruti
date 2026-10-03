import asyncio
from api.db import db_client
from sqlalchemy import text

async def check():
    async with db_client.async_session() as session:
        res = await session.execute(text("SELECT id, name, tool_json FROM tools;"))
        for row in res.fetchall():
            print(f"\nTool id={row[0]}, name={row[1]}")
            print(json.dumps(row[2], indent=2))

if __name__ == "__main__":
    asyncio.run(check())
