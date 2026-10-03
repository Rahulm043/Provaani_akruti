import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def dump():
    async with db_client.async_session() as session:
        res = await session.execute(text("SELECT workflow_definition FROM workflows WHERE id = 1;"))
        row = res.first()
        wf = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        with open("/tmp/wf1_current_prompt.txt", "w", encoding="utf-8") as f:
            f.write(wf["nodes"][0]["data"]["prompt"])
        print("WROTE_TO_TMP")

if __name__ == "__main__":
    asyncio.run(dump())
