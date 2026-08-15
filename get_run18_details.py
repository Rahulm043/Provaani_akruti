import asyncio, json
from api.db import db_client

async def main():
    rows = await db_client.execute_raw_query("SELECT id, logs FROM workflow_runs WHERE id = 18;")
    if rows:
        events = rows[0].get("logs", {}).get("realtime_feedback_events", [])
        for ev in events:
            if ev.get("type") in ("rtf-bot-text", "rtf-user-transcription", "rtf-node-transition"):
                print(f"[{ev.get('type')}] -> {json.dumps(ev.get('payload'), ensure_ascii=False)}")

if __name__ == "__main__":
    asyncio.run(main())
