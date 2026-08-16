import asyncio, json
from datetime import datetime
from api.db import db_client

async def main():
    rows = await db_client.execute_raw_query("""
        SELECT id, mode, state, created_at, logs 
        FROM workflow_runs 
        WHERE mode = 'plivo' AND is_completed = true 
        ORDER BY id DESC;
    """)
    print(f"Total completed Plivo calls: {len(rows)}\n")
    
    call_stats = []
    for r in rows:
        run_id = r["id"]
        logs = r.get("logs") or {}
        if isinstance(logs, str):
            logs = json.loads(logs)
        events = logs.get("realtime_feedback_events", [])
        if not events:
            continue
            
        bot_chars = 0
        user_words = 0
        llm_turns = 0
        user_turns = 0
        prompt_tokens_est = 0
        completion_tokens_est = 0
        
        timestamps = []
        for ev in events:
            t_str = ev.get("timestamp")
            if t_str:
                try:
                    timestamps.append(datetime.fromisoformat(t_str.replace("Z", "+00:00")))
                except:
                    pass
                    
            ev_type = ev.get("type")
            payload = ev.get("payload") or {}
            if ev_type == "rtf-bot-text":
                text = payload.get("text", "")
                bot_chars += len(text)
                llm_turns += 1
                completion_tokens_est += len(text.split()) * 1.3
            elif ev_type == "rtf-user-transcription":
                text = payload.get("text", "")
                user_words += len(text.split())
                user_turns += 1
        
        duration_sec = 0
        if len(timestamps) >= 2:
            duration_sec = (max(timestamps) - min(timestamps)).total_seconds()
        
        # Estimate input prompt tokens across turns: base prompt ~350 tokens + history growth (~50 tokens per turn)
        for turn_idx in range(llm_turns):
            prompt_tokens_est += 350 + (turn_idx * 50)
            
        if duration_sec > 5:  # filter test blips
            call_stats.append({
                "run_id": run_id,
                "duration_sec": duration_sec,
                "duration_min": duration_sec / 60.0,
                "bot_chars": bot_chars,
                "user_words": user_words,
                "llm_turns": llm_turns,
                "user_turns": user_turns,
                "prompt_tokens": prompt_tokens_est,
                "completion_tokens": completion_tokens_est
            })
            print(f"Run {run_id:2d}: Duration={duration_sec:5.1f}s ({duration_sec/60:4.2f}m) | Turns={llm_turns} | BotChars={bot_chars:4d} | UserWords={user_words:3d} | PromptTok={prompt_tokens_est:4.0f} | ComplTok={completion_tokens_est:3.0f}")

    if not call_stats:
        print("No calls with duration > 5s found.")
        return

    total_duration_sec = sum(c["duration_sec"] for c in call_stats)
    total_duration_min = total_duration_sec / 60.0
    total_bot_chars = sum(c["bot_chars"] for c in call_stats)
    total_prompt_tokens = sum(c["prompt_tokens"] for c in call_stats)
    total_completion_tokens = sum(c["completion_tokens"] for c in call_stats)
    total_turns = sum(c["llm_turns"] for c in call_stats)
    avg_duration_sec = total_duration_sec / len(call_stats)

    print("\n" + "="*70)
    print(f"AGGREGATE SUMMARY ACROSS {len(call_stats)} CALLS:")
    print(f"Total Call Duration: {total_duration_sec:.1f} sec ({total_duration_min:.2f} minutes)")
    print(f"Average Call Duration: {avg_duration_sec:.1f} sec ({avg_duration_sec/60:.2f} minutes)")
    print(f"Total Bot Characters (TTS): {total_bot_chars:,} chars")
    print(f"Total Estimated Prompt Tokens (LLM): {total_prompt_tokens:,.0f} tokens")
    print(f"Total Estimated Completion Tokens (LLM): {total_completion_tokens:,.0f} tokens")
    print(f"Total Conversation Turns: {total_turns} turns")
    print(f"Average Bot Characters per minute of call: {total_bot_chars / total_duration_min:.1f} chars/min")
    print(f"Average Prompt Tokens per minute of call: {total_prompt_tokens / total_duration_min:.1f} tokens/min")
    print(f"Average Completion Tokens per minute of call: {total_completion_tokens / total_duration_min:.1f} tokens/min")
    print("="*70)

if __name__ == "__main__":
    asyncio.run(main())
