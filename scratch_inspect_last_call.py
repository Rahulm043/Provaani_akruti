import asyncio
import json
import sys
from api.db import db_client
from sqlalchemy import text

sys.stdout.reconfigure(encoding='utf-8')

async def main():
    async with db_client.async_session() as session:
        res = await session.execute(text("SELECT id, created_at, transcript_url, gathered_context, logs FROM workflow_runs ORDER BY id DESC LIMIT 2;"))
        rows = res.fetchall()
        for r in rows:
            run_id = r[0]
            created_at = r[1]
            transcript_url = r[2]
            gathered_context = r[3]
            logs = r[4]
            
            print(f"\n==========================================")
            print(f" Workflow Run ID: {run_id} | Time: {created_at}")
            print(f" Transcript URL: {transcript_url}")
            print(f" Gathered Context: {json.dumps(gathered_context, indent=2)}")
            print(f"------------------------------------------")
            
            # Print conversation transcript/turns from logs
            if isinstance(logs, str):
                logs = json.loads(logs)
            
            events = logs.get("realtime_feedback_events", []) if logs else []
            print(f" Total Feedback Events: {len(events)}")
            for ev in events:
                ev_type = ev.get("type")
                payload = ev.get("payload", {})
                ts = ev.get("timestamp")
                if ev_type == "rtf-bot-text":
                    print(f" [{ts}] BOT: {payload.get('text')}")
                elif ev_type == "rtf-user-text" or "user" in ev_type:
                    print(f" [{ts}] USER: {payload.get('text')}")
                elif "tool" in ev_type or "function" in ev_type:
                    print(f" [{ts}] TOOL EVENT: {ev_type} -> {payload}")
                elif ev_type == "rtf-node-transition":
                    print(f" [{ts}] NODE: {payload.get('node_name')} (ID: {payload.get('node_id')})")
                elif "dtmf" in str(ev).lower():
                    print(f" [{ts}] DTMF EVENT: {ev}")

asyncio.run(main())
