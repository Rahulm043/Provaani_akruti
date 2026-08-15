import asyncio, json
from api.db import db_client

async def main():
    for run_id in [26, 25]:
        rows = await db_client.execute_raw_query(f"SELECT id, mode, state, gathered_context, logs FROM workflow_runs WHERE id = {run_id};")
        if not rows:
            continue
        row = rows[0]
        print(f"\n==================== RUN {run_id} (mode: {row.get('mode')}, state: {row.get('state')}) ====================")
        print("GATHERED CONTEXT:", json.dumps(row.get("gathered_context"), ensure_ascii=False, indent=2))
        logs = row.get("logs") or {}
        if isinstance(logs, str):
            logs = json.loads(logs)
        events = logs.get("realtime_feedback_events", [])
        print("\nCONVERSATION TURNS:")
        for ev in events:
            ev_type = ev.get("type")
            payload = ev.get("payload") or {}
            turn = ev.get("turn")
            node = ev.get("node_name")
            if ev_type == "rtf-node-transition":
                print(f"[Turn {turn} | {node}] -> TRANSITION to {payload.get('node_name')}")
            elif ev_type == "rtf-bot-text":
                print(f"[Turn {turn} | {node}] BOT: {payload.get('text')}")
            elif ev_type == "rtf-user-transcription":
                print(f"[Turn {turn} | {node}] USER: {payload.get('text')}")
            elif ev_type == "rtf-tool-call":
                print(f"[Turn {turn} | {node}] TOOL: {payload}")

if __name__ == "__main__":
    asyncio.run(main())
