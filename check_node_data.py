import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def check():
    async with db_client.async_session() as session:
        res = await session.execute(text("SELECT workflow_definition FROM workflows WHERE id = 1;"))
        row = res.first()
        wf = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        node = wf["nodes"][0]
        print("NODE KEYS:", list(node.keys()))
        ndata = node.get("data", {})
        print("DATA KEYS:", list(ndata.keys()))
        for k, v in ndata.items():
            if k != "prompt":
                print(f"  {k}: {v}")

if __name__ == "__main__":
    asyncio.run(check())
