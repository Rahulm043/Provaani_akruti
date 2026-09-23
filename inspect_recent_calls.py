import asyncio, json
from api.db import db_client

async def main():
    rows = await db_client.execute_raw_query("SELECT id, mode, state, gathered_context, logs FROM workflow_runs ORDER BY id DESC LIMIT 3;")
    for row in rows:
        run_id = row.get("id")
        print(f"\n==================== RUN {run_id} (state: {row.get('state')}) ====================")
        print("GATHERED CONTEXT:", json.dumps(row.get("gathered_context"), ensure_ascii=False, indent=2))
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
            elif ev_type == "rtf-ttfb-metric":
                print(f"[Turn {turn}] TTFB: {payload.get('ttfb_seconds')}s (model: {payload.get('model')})")
            elif ev_type == "rtf-tool-call":
                print(f"[Turn {turn}] TOOL: {payload}")

if __name__ == "__main__":
    asyncio.run(main())
