"""
Post-call analysis service for Akruti Aesthetics (Workflow 5) & Sukanya voice agents.
Evaluates transcripts via TypeSafe AI Jev (System One) model in milliseconds.
Handles deterministic DTMF/regex phone number extraction and async WhatsApp delivery.
Stores results in SQLite DB and exposes HTTP endpoints on port 8001.
"""

import asyncio
import json
import logging
import os
import re
import sqlite3
from datetime import datetime

import httpx

from whatsapp_service import (
    send_whatsapp_clinic_details,
    send_whatsapp_appointment_confirmation,
    send_whatsapp_appointment_details,
    send_whatsapp_clinic_and_appointment_details,
    TIMINGS_STATE,
    save_timings_state,
    normalize_phone_number
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "/data/analysis.db")
TYPESAFE_API_KEY = os.getenv("TYPESAFE_API_KEY") or os.getenv("JEV_API_KEY", "")
DOGRAH_API_BASE = os.getenv("DOGRAH_API_BASE", "http://api:8000")
DOGRAH_API_KEY = os.getenv("DOGRAH_API_KEY", "")

JEV_ENDPOINT = "https://api.typesafe.ai/v1/systemone"
JEV_MODEL = "jev-latest"

JEV_QUESTIONS = {
    "should_send_whatsapp": {
        "type": "noul",
        "instructions": "Did the caller request clinic details, doctor info, or consultation timings to be sent via WhatsApp, or did the agent promise to send them, or was a phone number provided for WhatsApp?"
    },
    "clinic_location": {
        "type": "choice",
        "instructions": "Which clinic branch did the caller inquire about or express interest in visiting?",
        "criteria": {
            "durgapur": "Durgapur branch (City Centre, Maulana Azad Sarani)",
            "burdwan": "Burdwan branch (Power House Para, Near Park Nursing Home)",
            "both": "Both Durgapur and Burdwan branches",
            "unspecified": "No specific clinic branch mentioned"
        }
    },
    "procedure_type": {
        "type": "choice",
        "instructions": "What specific aesthetic, plastic surgery, hair, skin, or reconstructive procedure or consultation did the caller ask about or discuss?",
        "criteria": {
            "hair_transplant": "Hair Transplant (FUE / FUT)",
            "prp_therapy": "PRP Hair or Skin Therapy",
            "gynaecomastia": "Gynaecomastia (Male Breast Reduction)",
            "rhinoplasty": "Rhinoplasty (Nose Reshaping / Nose Job)",
            "liposuction": "Liposuction (Body Contouring / Fat Removal)",
            "tummy_tuck": "Tummy Tuck (Abdominoplasty / Mini Tummy Tuck)",
            "facelift": "Facelift (Rhytidectomy / Mini Face Lift)",
            "blepharoplasty": "Asian Eyelid Blepharoplasty (Double Eyelid / Bag Removal)",
            "dimpleplasty": "Dimpleplasty (Dimple Creation)",
            "buccal_fat_removal": "Buccal Fat Pad Removal (Cheek Reduction)",
            "breast_augmentation": "Breast Augmentation (Implants / Fat Transfer)",
            "breast_reduction_lift": "Breast Reduction / Breast Lift (Mastopexy)",
            "mole_cyst_removal": "Mole / Lipoma / Sebaceous Cyst Excision",
            "botox_fillers": "Botox / Dermal Fillers",
            "acne_scar_revision": "Acne & Acne Scar Revision",
            "chemical_peels_facials": "Chemical Peels / Medical Facials / Skin Glow",
            "cryolipolysis": "Cryolipolysis (Non-Surgical Fat Freezing)",
            "beard_eyebrow_transplant": "Beard / Moustache / Eyebrow Transplant or Micropigmentation",
            "burn_reconstruction": "Burn Deformity / Post-Burn Scar Contracture Release",
            "maxillofacial_trauma": "Maxillofacial & Facial Trauma Reconstruction",
            "general_consultation": "General Plastic & Cosmetic Surgery Consultation",
            "other_unspecified": "Other or unspecified inquiry"
        }
    },
    "preferred_language": {
        "type": "choice",
        "instructions": "What was the caller's primary spoken language during the conversation?",
        "criteria": {
            "bengali": "Bengali (Bangla)",
            "hindi": "Hindi",
            "english": "English"
        }
    }
}


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
                procedure_type TEXT,
                clinic_location TEXT,
                should_send_whatsapp INTEGER DEFAULT 0,
                whatsapp_target_phone TEXT,
                whatsapp_status TEXT,
                raw_jev_json TEXT,
                error TEXT,
                duration_ms INTEGER,
                created_at TEXT,
                analyzed_at TEXT
            )
        """)
        # Ensure migration columns exist if DB was previously created
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(call_analysis);")
        existing_cols = {row[1] for row in cur.fetchall()}
        
        new_cols = [
            ("procedure_type", "TEXT"),
            ("clinic_location", "TEXT"),
            ("should_send_whatsapp", "INTEGER DEFAULT 0"),
            ("whatsapp_target_phone", "TEXT"),
            ("whatsapp_status", "TEXT"),
            ("raw_jev_json", "TEXT"),
        ]
        for col_name, col_type in new_cols:
            if col_name not in existing_cols:
                try:
                    conn.execute(f"ALTER TABLE call_analysis ADD COLUMN {col_name} {col_type};")
                    logger.info(f"Added column {col_name} to call_analysis table")
                except Exception as e:
                    logger.warning(f"Column migration warning for {col_name}: {e}")
                    
        conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON call_analysis(status)")
    logger.info("SQLite DB ready with Jev schema extensions")


def extract_target_phone(transcript: str, metadata: dict = None) -> str:
    """Extract phone number from DTMF keypad logs, transcript text, or call metadata."""
    if not transcript and not metadata:
        return ""

    # Priority 1: Keypad DTMF tag in transcript
    dtmf_match = re.search(r"\[(?:Keypad Input Received|DTMF|Keypad):\s*([0-9]{10})\]", transcript or "", re.IGNORECASE)
    if dtmf_match:
        phone = dtmf_match.group(1).strip()
        logger.info(f"Extracted phone from DTMF tag: {phone}")
        return normalize_phone_number(phone)

    # Priority 2: 10-digit Indian phone number pattern in transcript
    text_matches = re.findall(r"\b[6-9]\d{9}\b", transcript or "")
    if text_matches:
        phone = text_matches[-1] # Take the most recently spoken/entered number
        logger.info(f"Extracted phone from transcript regex: {phone}")
        return normalize_phone_number(phone)

    # Priority 3: Metadata / Caller ID fallback
    meta = metadata or {}
    meta_phone = (
        meta.get("whatsapp_number") or
        meta.get("caller_number") or
        meta.get("from_phone") or
        meta.get("phone_number")
    )
    if meta_phone:
        logger.info(f"Using fallback phone from metadata: {meta_phone}")
        return normalize_phone_number(meta_phone)

    return ""


async def analyze_call(run_id: int, transcript: str = "", metadata: dict = None):
    conn = sqlite3.connect(DB_PATH)
    meta = metadata or {}
    wf_id = meta.get("workflow_id", 5)

    conn.execute(
        "INSERT OR REPLACE INTO call_analysis (run_id, workflow_id, status, created_at) VALUES (?, ?, 'processing', ?)",
        (run_id, wf_id, datetime.utcnow().isoformat()),
    )
    conn.commit()

    start_time = datetime.utcnow()
    try:
        call_transcript = (transcript or "").strip()
        
        # If no transcript provided in body, try to fetch from public token or API
        if not call_transcript:
            logger.info(f"No transcript provided in payload for run {run_id}, attempting fallback fetch...")
            # Fallback transcript string placeholder if not available
            call_transcript = f"Call Run ID {run_id} completed."

        logger.info(f"Starting Jev analysis for run {run_id} (workflow {wf_id}). Transcript length: {len(call_transcript)} chars")

        jev_payload = {
            "state": call_transcript,
            "model": JEV_MODEL,
            "questions": JEV_QUESTIONS
        }

        api_key = TYPESAFE_API_KEY
        if not api_key:
            # Try reading from .env directly if not in env
            try:
                with open("/home/rahul/Provaani_akruti/.env", "r") as f:
                    for line in f:
                        if line.startswith("TYPESAFE_API_KEY=") or line.startswith("JEV_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
            except Exception:
                pass

        if not api_key:
            raise ValueError("TYPESAFE_API_KEY is not configured")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AkrutiPostCall/1.0"
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(JEV_ENDPOINT, headers=headers, json=jev_payload)
            if resp.status_code != 200:
                raise Exception(f"TypeSafe API returned {resp.status_code}: {resp.text}")
            jev_data = resp.json()

        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Jev response received for run {run_id} in {elapsed:.2f}s")

        answers = jev_data.get("answers", {})
        
        # Parse answers
        should_send_ans = answers.get("should_send_whatsapp", {})
        noul_val = should_send_ans.get("noul", 0.0)
        should_send_whatsapp = 1 if noul_val >= 0.5 else 0

        clinic_ans = answers.get("clinic_location", {})
        clinic_location = clinic_ans.get("choice", "unspecified")

        procedure_ans = answers.get("procedure_type", {})
        procedure_type = procedure_ans.get("choice", "other_unspecified")

        lang_ans = answers.get("preferred_language", {})
        preferred_language = lang_ans.get("choice", "bengali")

        # Extract target phone number
        target_phone = extract_target_phone(call_transcript, meta)
        whatsapp_status = "skipped"

        # Dispatch WhatsApp if requested
        if should_send_whatsapp and target_phone:
            logger.info(f"Jev confirmed WhatsApp dispatch (noul={noul_val:.2f}) for run {run_id} to {target_phone} (Branch: {clinic_location}, Procedure: {procedure_type})")
            
            try:
                wa_res = await send_whatsapp_clinic_and_appointment_details(
                    phone_number=target_phone
                )
                if wa_res.get("success"):
                    whatsapp_status = f"sent (id: {wa_res.get('message_id')})"
                    logger.info(f"WhatsApp template clinic_and_appointment_details sent successfully to {target_phone}")
                else:
                    whatsapp_status = f"failed: {wa_res.get('error')}"
                    logger.warning(f"WhatsApp dispatch failed for {target_phone}: {wa_res.get('error')}")
            except Exception as wa_err:
                whatsapp_status = f"error: {wa_err}"
                logger.error(f"Error during WhatsApp sending for run {run_id}: {wa_err}")
        elif should_send_whatsapp and not target_phone:
            whatsapp_status = "pending_no_phone"
            logger.warning(f"WhatsApp was requested (noul={noul_val:.2f}) but no valid phone number was found for run {run_id}")

        summary = f"Procedure: {procedure_type}, Clinic: {clinic_location}, Language: {preferred_language}, WhatsApp: {whatsapp_status}"

        conn.execute(
            """UPDATE call_analysis SET
               status='completed', transcript=?, summary=?, sentiment=?,
               language=?, procedure_type=?, clinic_location=?,
               should_send_whatsapp=?, whatsapp_target_phone=?, whatsapp_status=?,
               raw_jev_json=?, analyzed_at=?
               WHERE run_id=?""",
            (
                call_transcript,
                summary,
                "interested" if should_send_whatsapp else "neutral",
                preferred_language,
                procedure_type,
                clinic_location,
                should_send_whatsapp,
                target_phone,
                whatsapp_status,
                json.dumps(jev_data),
                datetime.utcnow().isoformat(),
                run_id,
            ),
        )
        conn.commit()
        logger.info(f"Run {run_id} completed post-call Jev processing in {elapsed:.2f}s")

    except Exception as e:
        logger.error(f"Post-call analysis failed for run {run_id}: {e}")
        conn.execute(
            "UPDATE call_analysis SET status='failed', error=? WHERE run_id=?",
            (str(e)[:500], run_id),
        )
        conn.commit()
    finally:
        conn.close()


async def main():
    init_db()
    from aiohttp import web

    async def handle_send_whatsapp(request):
        try:
            data = await request.json()
        except Exception:
            data = {}
        phone_number = data.get("phone_number") or data.get("to") or data.get("number")
        template_type = data.get("template_type") or data.get("type")
        caller_name = data.get("caller_name") or data.get("patient_name") or data.get("name")
        appointment_datetime = data.get("appointment_datetime") or data.get("appointment_date_time") or data.get("time")
        branch = data.get("branch") or data.get("branch_id") or data.get("branch_name")

        if not phone_number:
            return web.json_response({"status": "error", "message": "phone_number is required"}, status=400)

        durgapur_timings = data.get("durgapur_timings")
        burdwan_timings = data.get("burdwan_timings")

        if template_type == "appointment_confirmation" or (appointment_datetime and caller_name):
            res = await send_whatsapp_appointment_confirmation(
                phone_number=phone_number,
                patient_name=caller_name,
                appointment_datetime=appointment_datetime,
                branch_id_or_name=branch
            )
        elif template_type == "appointment_details":
            res = await send_whatsapp_appointment_details(
                phone_number=phone_number,
                branch_id_or_name=branch,
                durgapur_timings=durgapur_timings,
                burdwan_timings=burdwan_timings
            )
        else:
            procedure = data.get("procedure_of_interest") or data.get("procedure")
            res = await send_whatsapp_clinic_details(
                phone_number=phone_number,
                caller_name=caller_name,
                procedure_of_interest=procedure,
                durgapur_timings=durgapur_timings,
                burdwan_timings=burdwan_timings
            )
        return web.json_response(res)

    async def handle_update_timings(request):
        try:
            payload = await request.json()
            if isinstance(payload, dict):
                for k, v in payload.items():
                    if v and isinstance(v, str):
                        TIMINGS_STATE[k] = v.strip()
                save_timings_state(TIMINGS_STATE)
                logger.info(f"Updated WhatsApp timings state: {TIMINGS_STATE}")
                return web.json_response({"status": "ok", "timings": TIMINGS_STATE})
            return web.json_response({"error": "Invalid payload, dictionary expected"}, status=400)
        except Exception as e:
            logger.error(f"Error updating timings state: {e}")
            return web.json_response({"error": str(e)}, status=400)

    async def handle_get_timings(request):
        return web.json_response({"status": "ok", "timings": TIMINGS_STATE})

    async def handle_analyze(request):
        try:
            run_id = int(request.match_info["run_id"])
        except (ValueError, KeyError):
            return web.json_response({"error": "Invalid run_id"}, status=400)
        
        try:
            body = await request.json()
        except Exception:
            body = {}

        transcript = body.get("transcript", "")
        metadata = body.get("metadata", {})

        asyncio.create_task(analyze_call(run_id, transcript=transcript, metadata=metadata))
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
            web.post("/send-whatsapp", handle_send_whatsapp),
            web.post("/update-timings", handle_update_timings),
            web.get("/timings", handle_get_timings),
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
    logger.info("Analysis & Jev Post-Call Service started on :8001")
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
        "procedure_type",
        "clinic_location",
        "should_send_whatsapp",
        "whatsapp_target_phone",
        "whatsapp_status",
        "raw_jev_json",
        "error",
        "duration_ms",
        "created_at",
        "analyzed_at",
    ]
    # Slice or pad dynamically to match actual row length
    cols = cols[:len(row)]
    d = dict(zip(cols, row))
    if d.get("key_points") and isinstance(d["key_points"], str):
        try:
            d["key_points"] = json.loads(d["key_points"])
        except Exception:
            d["key_points"] = []
    if d.get("raw_jev_json") and isinstance(d["raw_jev_json"], str):
        try:
            d["raw_jev_json"] = json.loads(d["raw_jev_json"])
        except Exception:
            pass
    return d


if __name__ == "__main__":
    asyncio.run(main())
