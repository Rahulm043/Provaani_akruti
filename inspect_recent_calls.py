import asyncio, json
from api.db import db_client

async def main():
    for run_id in [36]:
        rows = await db_client.execute_raw_query(f"SELECT id, mode, state, gathered_context, logs FROM workflow_runs WHERE id = {run_id};")
        if not rows:
            continue
        row = rows[0]
        print(f"\n==================== RUN {run_id} ====================")
        logs = row.get("logs") or {}
        if isinstance(logs, str):
            logs = json.loads(logs)
        events = logs.get("realtime_feedback_events", [])
        for ev in events:
            ev_type = ev.get("type")
            payload = ev.get("payload") or {}
            turn = ev.get("turn")
            if ev_type == "rtf-bot-text":
                print(f"[Turn {turn}] BOT: {payload.get('text')}")
            elif ev_type == "rtf-user-transcription":
                print(f"[Turn {turn}] USER: {payload.get('text')}")

if __name__ == "__main__":
    asyncio.run(main())
