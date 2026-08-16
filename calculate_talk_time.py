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
    
    print(f"Analyzing {len(rows)} completed Plivo calls...\n")
    
    call_breakdowns = []
    
    for r in rows:
        run_id = r["id"]
        logs = r.get("logs") or {}
        if isinstance(logs, str):
            logs = json.loads(logs)
        events = logs.get("realtime_feedback_events", [])
        if not events:
            continue
            
        timestamps = []
        bot_texts = []
        user_texts = []
        
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
                bot_texts.append(payload.get("text", ""))
            elif ev_type == "rtf-user-transcription":
                user_texts.append(payload.get("text", ""))
                
        if len(timestamps) < 2:
            continue
            
        call_duration_sec = (max(timestamps) - min(timestamps)).total_seconds()
        if call_duration_sec < 5:
            continue
            
        total_bot_chars = sum(len(t) for t in bot_texts)
        total_bot_words = sum(len(t.split()) for t in bot_texts)
        total_user_words = sum(len(t.split()) for t in user_texts)
        
        # Audio duration models:
        # 1. Bot speaking speed: Smallest AI TTS @ 0.9 speed generates ~13.5 characters per second (or ~2.3 words per second / ~140 wpm).
        bot_speaking_sec = total_bot_chars / 13.5
        
        # 2. User speaking speed: Indian English/Hindi conversational speech is ~2.5 words per second (~150 wpm) + ~0.5s pause per utterance.
        user_speaking_sec = (total_user_words / 2.5) + (len(user_texts) * 0.4)
        
        # Ensure sum does not exceed call duration
        silence_or_network_sec = max(0.0, call_duration_sec - bot_speaking_sec - user_speaking_sec)
        
        bot_pct = (bot_speaking_sec / call_duration_sec) * 100
        user_pct = (user_speaking_sec / call_duration_sec) * 100
        silence_pct = (silence_or_network_sec / call_duration_sec) * 100
        
        call_breakdowns.append({
            "run_id": run_id,
            "duration": call_duration_sec,
            "bot_sec": bot_speaking_sec,
            "user_sec": user_speaking_sec,
            "silence_sec": silence_or_network_sec,
            "bot_pct": bot_pct,
            "user_pct": user_pct,
            "silence_pct": silence_pct,
            "bot_chars": total_bot_chars,
            "user_words": total_user_words
        })
        
        print(f"Run {run_id:2d} ({call_duration_sec:5.1f}s): Bot={bot_speaking_sec:4.1f}s ({bot_pct:4.1f}%) | User={user_speaking_sec:4.1f}s ({user_pct:4.1f}%) | Silence/Thinking={silence_or_network_sec:4.1f}s ({silence_pct:4.1f}%)")

    total_call_sec = sum(c["duration"] for c in call_breakdowns)
    total_bot_sec = sum(c["bot_sec"] for c in call_breakdowns)
    total_user_sec = sum(c["user_sec"] for c in call_breakdowns)
    total_silence_sec = sum(c["silence_sec"] for c in call_breakdowns)
    
    total_speech_sec = total_bot_sec + total_user_sec
    
    print("\n" + "="*75)
    print(f"AGGREGATE TALK-TIME RATIO OVER {len(call_breakdowns)} CALLS ({total_call_sec:.1f} sec total):")
    print(f"1. As % of Total Call Time:")
    print(f"   - Bot Speaking Time:       {total_bot_sec:6.1f}s  -> {total_bot_sec / total_call_sec * 100:5.2f}%")
    print(f"   - User Speaking Time:      {total_user_sec:6.1f}s  -> {total_user_sec / total_call_sec * 100:5.2f}%")
    print(f"   - Silence / Latency / Gap: {total_silence_sec:6.1f}s  -> {total_silence_sec / total_call_sec * 100:5.2f}%")
    print(f"\n2. As % of Active Speech Only (excluding silence/gaps):")
    print(f"   - Bot Share of Speech:     {total_bot_sec / total_speech_sec * 100:5.2f}%")
    print(f"   - User Share of Speech:    {total_user_sec / total_speech_sec * 100:5.2f}%")
    print("="*75)

if __name__ == "__main__":
    asyncio.run(main())
