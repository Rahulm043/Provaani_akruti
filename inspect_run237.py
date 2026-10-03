import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def inspect_run():
    async with db_client.async_session() as session:
        res = await session.execute(text("SELECT logs, gathered_context, usage_info FROM workflow_runs WHERE id = 237;"))
        row = res.first()
        if row:
            logs = row[0] if isinstance(row[0], (dict, list)) else json.loads(row[0] or "{}")
            print("LOGS TYPE:", type(logs))
            if isinstance(logs, dict):
                print("LOGS KEYS:", list(logs.keys()))
                for k, v in logs.items():
                    print(f"Key {k}: {str(v)[:200]}")
            elif isinstance(logs, list):
                print(f"Total log lines: {len(logs)}")
                for l in logs[-30:]:
                    print(l)
            print("\nGATHERED CONTEXT:", row[1])
            print("\nUSAGE INFO:", row[2])

if __name__ == "__main__":
    asyncio.run(inspect_run())
