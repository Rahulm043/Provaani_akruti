import asyncio, json, sys
from api.db import db_client

async def main():
    run = await db_client.get_workflow_run(10, 1)
    print("=== RUN 10 TURNS ===")
    for t in (run.session_data or {}).get("turns", []):
        u = (t.get("user_message") or {}).get("text")
        a = (t.get("assistant_message") or {}).get("text")
        print(f"User: {u}")
        print(f"Assistant: {a}")
        print(f"Events: {t.get('events')}")
        print("---")

if __name__ == "__main__":
    asyncio.run(main())
