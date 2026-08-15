import asyncio, json
from api.db import db_client

async def main():
    rows = await db_client.execute_raw_query("SELECT id, logs, gathered_context, extra FROM workflow_runs WHERE id = 10;")
    if rows:
        row = rows[0]
        print("=== GATHERED CONTEXT ===")
        print(json.dumps(row.get("gathered_context"), indent=2))
        print("=== LOGS ===")
        logs = row.get("logs")
        if isinstance(logs, str):
            logs = json.loads(logs)
        print(json.dumps(logs, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
