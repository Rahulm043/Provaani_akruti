"""
Post-call analysis service for Sukanya voice agent.
Downloads call recordings, sends to Gemini 3.1 Flash Lite.
Stores results in SQLite, exposed via HTTP API.
"""

import asyncio
import json
import logging
import os
import sqlite3
from datetime import datetime

import httpx
import google.genai as genai
from google.genai import types

from whatsapp_service import send_whatsapp_clinic_details

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "/data/analysis.db")
API_KEY = os.getenv("GOOGLE_API_KEY", "")
DOGRAH_API_BASE = os.getenv("DOGRAH_API_BASE", "http://api:8000")
DOGRAH_API_KEY = os.getenv("DOGRAH_API_KEY", "")

MODEL = "models/gemini-3.1-flash-lite-preview"

SYSTEM_PROMPT = """You are a call analysis system for an outbound calling agent at Sukanya Classes (a coaching institute in Durgapur, India). The agent (Sudipta) calls parents to discuss their child's education.

Analyze this call recording and return ONLY valid JSON with this structure:
{
    "transcript": "Full transcript of the conversation. Format as: Agent: [text] Caller: [text]. Capture everything said.",
    "summary": "One to two sentence summary of the call. Include child details if mentioned.",
    "sentiment": "interested|not_interested|irrelevant|unsure",
    "key_points": ["point 1", "point 2", "point 3"],
    "language": "primary language(s) used, e.g., bengali, bengali_english, hindi, english"
}

SENTIMENT RULES (be strict):
- "interested" = Caller asked questions, wanted callback/visit, discussed child's needs positively
- "not_interested" = Caller explicitly declined, made excuses, said not to call again
- "irrelevant" = Wrong number, disconnected immediately, unrelated call, no conversation
- "unsure" = Call too brief (<10 seconds), ambiguous, or couldn't determine interest

IMPORTANT: Return ONLY the JSON object. No markdown, no code fences, no extra text."""


def init_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS call_analysis (
                run_id INTEGER PRIMARY KEY,
                workflow_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending',
                transcript TEXT,
                summary TEXT,
                sentiment TEXT,
                key_points TEXT DEFAULT '[]',
                language TEXT,
                error TEXT,
                duration_ms INTEGER,
                created_at TEXT,
                analyzed_at TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON call_analysis(status)")
    logger.info("SQLite DB ready")


async def analyze_call(run_id: int, client):
    conn = sqlite3.connect(DB_PATH)

    # Check if already analyzed
    row = conn.execute(
        "SELECT status, transcript FROM call_analysis WHERE run_id = ?", (run_id,)
    ).fetchone()
    if row and row[0] == "completed" and row[1]:
        logger.info(f"Run {run_id} already analyzed, skipping")
        conn.close()
        return

    conn.execute(
        "INSERT OR REPLACE INTO call_analysis (run_id, workflow_id, status, created_at) VALUES (?, ?, 'processing', ?)",
        (run_id, 1, datetime.utcnow().isoformat()),
    )
    conn.commit()

    try:
        # Get recording
        async with httpx.AsyncClient(timeout=30.0) as http:
            run_resp = await http.get(
                f"{DOGRAH_API_BASE}/api/v1/workflow/1/runs/{run_id}",
                headers={"x-api-key": DOGRAH_API_KEY},
            )
            if run_resp.status_code != 200:
                raise Exception(f"Failed to get run: {run_resp.status_code}")
            run_data = run_resp.json()
            public_token = run_data.get("public_access_token")
            if not public_token:
                raise Exception("No public_access_token")

            recording_url = f"{DOGRAH_API_BASE}/api/v1/public/download/workflow/{public_token}/recording"
            # API returns 302 redirect to localhost:9000 — we need to reach minio:9000
            audio_resp = await http.get(recording_url, follow_redirects=False)
            if audio_resp.status_code == 302:
                redirect_url = audio_resp.headers.get("location", "")
                redirect_url = redirect_url.replace(
                    "localhost:9000", "minio:9000"
                ).replace("127.0.0.1:9000", "minio:9000")
                audio_resp = await http.get(redirect_url, timeout=60)
            if audio_resp.status_code != 200:
                raise Exception(f"Failed to download audio: {audio_resp.status_code}")
            audio_bytes = audio_resp.content
            duration_ms = (
                run_data.get("cost_info", {}).get("call_duration_seconds", 0) * 1000
            )

        # Send to Gemini
        start_time = datetime.utcnow()
        response = await client.aio.models.generate_content(
            model=MODEL,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part(text=SYSTEM_PROMPT),
                        types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
                    ],
                )
            ],
            config=types.GenerateContentConfig(temperature=0.2, max_output_tokens=4096),
        )
        elapsed = (datetime.utcnow() - start_time).total_seconds()

        # Parse response
        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        raw_text = raw_text.strip()

        try:
            analysis = json.loads(raw_text)
        except json.JSONDecodeError:
            import re

            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                analysis = json.loads(match.group())
            else:
                raise Exception(f"Could not parse JSON: {raw_text[:200]}...")

        sentiment = analysis.get("sentiment", "unsure")
        if sentiment not in ("interested", "not_interested", "irrelevant", "unsure"):
            sentiment = "unsure"

        conn.execute(
            """UPDATE call_analysis SET
               status='completed', transcript=?, summary=?, sentiment=?,
               key_points=?, language=?, duration_ms=?, analyzed_at=?
               WHERE run_id=?""",
            (
                analysis.get("transcript", ""),
                analysis.get("summary", ""),
                sentiment,
                json.dumps(analysis.get("key_points", [])),
                analysis.get("language", "unknown"),
                duration_ms,
                datetime.utcnow().isoformat(),
                run_id,
            ),
        )
        conn.commit()
        logger.info(f"Run {run_id} analyzed in {elapsed:.1f}s: sentiment={sentiment}")

        # Post-call WhatsApp Dispatch via Wasender API for Akruti Aesthetics (Workflow 6)
        initial_ctx = run_data.get("initial_context", {}) or {}
        caller_phone = (
            run_data.get("caller_number") or
            run_data.get("phone_number") or
            run_data.get("called_number") or
            initial_ctx.get("caller_number") or
            initial_ctx.get("phone_number")
        )
        wf_id = run_data.get("workflow_id", 1)
        gathered = run_data.get("gathered_context", {}) or {}
        caller_name = gathered.get("caller_name")
        procedure = gathered.get("procedure_of_interest")
        booking_requested = bool(gathered.get("booking_requested", False))
        preferred_time = gathered.get("preferred_date_time")

        if caller_phone:
            logger.info(f"Triggering WhatsApp dispatch for run {run_id} (workflow {wf_id}) to {caller_phone}")
            asyncio.create_task(
                send_whatsapp_clinic_details(
                    phone_number=caller_phone,
                    caller_name=caller_name,
                    procedure_of_interest=procedure,
                    booking_requested=booking_requested,
                    preferred_date_time=preferred_time
                )
            )

    except Exception as e:
        logger.error(f"Analysis failed for run {run_id}: {e}")
        conn.execute(
            "UPDATE call_analysis SET status='failed', error=? WHERE run_id=?",
            (str(e)[:500], run_id),
        )
        conn.commit()
    finally:
        conn.close()


async def main():
    init_db()
    client = genai.Client(api_key=API_KEY)

    from aiohttp import web

    async def handle_analyze(request):
        try:
            run_id = int(request.match_info["run_id"])
        except (ValueError, KeyError):
            return web.json_response({"error": "Invalid run_id"}, status=400)
        asyncio.create_task(analyze_call(run_id, client))
        return web.json_response({"status": "accepted", "run_id": run_id})

    async def handle_get_analysis(request):
        try:
            run_id = int(request.match_info["run_id"])
        except (ValueError, KeyError):
            return web.json_response({"error": "Invalid run_id"}, status=400)
        conn = sqlite3.connect(DB_PATH)
        row = conn.execute(
            "SELECT * FROM call_analysis WHERE run_id = ?", (run_id,)
        ).fetchone()
        conn.close()
        if not row:
            return web.json_response({"status": "not_found"}, status=404)
        return web.json_response(dict_from_row(row))

    async def handle_list_analyses(request):
        run_ids = request.rel_url.query.get("run_ids", "")
        conn = sqlite3.connect(DB_PATH)
        if run_ids:
            ids = [int(x.strip()) for x in run_ids.split(",") if x.strip()]
            placeholders = ",".join("?" * len(ids))
            rows = conn.execute(
                f"SELECT * FROM call_analysis WHERE run_id IN ({placeholders})", ids
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM call_analysis WHERE status='completed' ORDER BY analyzed_at DESC LIMIT 100"
            ).fetchall()
        conn.close()
        analyses = {str(row[0]): dict_from_row(row) for row in rows}
        return web.json_response({"analyses": analyses})

    async def handle_health(request):
        return web.json_response({"status": "ok"})

    app = web.Application()
    app.add_routes(
        [
            web.post("/analyze/{run_id}", handle_analyze),
            web.get("/analyze/{run_id}", handle_get_analysis),
            web.get("/analyze", handle_list_analyses),
            web.get("/health", handle_health),
        ]
    )

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8001)
    await site.start()
    logger.info("Analysis service started on :8001")
    await asyncio.Event().wait()


def dict_from_row(row):
    cols = [
        "run_id",
        "workflow_id",
        "status",
        "transcript",
        "summary",
        "sentiment",
        "key_points",
        "language",
        "error",
        "duration_ms",
        "created_at",
        "analyzed_at",
    ]
    d = dict(zip(cols, row))
    if d.get("key_points") and isinstance(d["key_points"], str):
        try:
            d["key_points"] = json.loads(d["key_points"])
        except:
            d["key_points"] = []
    if d.get("key_points"):
        d["key_points"] = list(d["key_points"])
    return d


if __name__ == "__main__":
    asyncio.run(main())
