"""
Clinic-Agnostic Prompt Compiler for Provaani Voice AI Receptionist.
Programmatically compiles ground truth clinic information, branch schedules,
and receptionist guidelines into a compact, low-latency voice agent prompt.
"""

from datetime import datetime, time as dtime
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional

DEFAULT_BRANCH_SCHEDULE = {
    "monday": [{"start": "10:00", "end": "19:00"}],
    "tuesday": [{"start": "10:00", "end": "19:00"}],
    "wednesday": [{"start": "10:00", "end": "19:00"}],
    "thursday": [{"start": "10:00", "end": "19:00"}],
    "friday": [{"start": "10:00", "end": "19:00"}],
    "saturday": [],
    "sunday": [],
}

DEFAULT_CLINIC_SETTINGS: Dict[str, Any] = {
    "clinic_name": "Aakruti Aesthetics & Plastic Surgery Clinic",
    "doctor_name": "Doctor Kaushal Priya Anand",
    "doctor_credentials": "M.B.B.S, M.S, M.Ch Plastic Surgery, 20+ years of excellence",
    "official_reception": "+91 90020 08137 / +91 90020 08147",
    "email": "akrutiaestheticsurgery@gmail.com",
    "branches": [
        {
            "id": "durgapur",
            "name": "Durgapur Clinic",
            "address": "First Floor, A-53, Maulana Azad Sarani, City Centre, Durgapur, West Bengal 713216",
        },
        {
            "id": "burdwan",
            "name": "Burdwan Clinic",
            "address": "S. S. Doctor Centre, Power House Para, Near Park Nursing Home, Burdwan",
        },
    ],
    "procedures": (
        "Rhinoplasty, Blepharoplasty, Facelift, Liposuction, Tummy Tuck, Gynaecomastia, "
        "Breast Augmentation/Reduction, Hair Transplant, PRP, Botox, Fillers, Chemical Peels, Acne Scar treatments."
    ),
    "appointment_config": {
        "enabled": True,
        "allow_booking": False,
        "schedule": {
            "durgapur": {
                "monday": [{"start": "09:00", "end": "19:00"}],
                "tuesday": [{"start": "09:00", "end": "19:00"}],
                "wednesday": [{"start": "09:00", "end": "19:00"}],
                "thursday": [{"start": "09:00", "end": "19:00"}],
                "friday": [{"start": "09:00", "end": "19:00"}],
                "saturday": [],
                "sunday": [],
            },
            "burdwan": {
                "monday": [],
                "tuesday": [],
                "wednesday": [],
                "thursday": [{"start": "14:00", "end": "18:00"}],
                "friday": [{"start": "09:00", "end": "19:00"}],
                "saturday": [{"start": "11:00", "end": "15:00"}],
                "sunday": [],
            },
        },
    },
}

_CACHED_CLINIC_SETTINGS: Optional[Dict[str, Any]] = None

def get_cached_clinic_settings() -> Dict[str, Any]:
    """Retrieve in-memory cached clinic settings or return defaults."""
    global _CACHED_CLINIC_SETTINGS
    if _CACHED_CLINIC_SETTINGS is not None:
        return _CACHED_CLINIC_SETTINGS
    return DEFAULT_CLINIC_SETTINGS

def set_cached_clinic_settings(settings: Dict[str, Any]) -> None:
    """Update in-memory cached clinic settings whenever modified via UI / API."""
    global _CACHED_CLINIC_SETTINGS
    if isinstance(settings, dict):
        _CACHED_CLINIC_SETTINGS = settings

DAY_KEYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def _parse_time_str(t_str: str) -> Optional[dtime]:
    if not t_str or not isinstance(t_str, str):
        return None
    try:
        parts = t_str.strip().split(":")
        h = int(parts[0])
        m = int(parts[1]) if len(parts) > 1 else 0
        return dtime(h, m)
    except Exception:
        return None

def compute_live_clinic_state_from_settings(
    settings: Optional[Dict[str, Any]] = None,
    now: Optional[datetime] = None
) -> str:
    """Procedurally calculate live clinic status and availability briefing from settings."""
    if settings is None:
        settings = get_cached_clinic_settings()

    if now is None:
        now = datetime.now(ZoneInfo("Asia/Kolkata"))

    current_day_idx = now.weekday()
    current_day_name = DAY_NAMES[current_day_idx]
    current_date_str = now.strftime("%B %d, %Y")
    current_time_str = now.strftime("%I:%M %p")
    now_time = now.time()

    doctor_name = settings.get("doctor_name", "Doctor Anand").strip()
    doc_display = "Doctor Anand" if "Anand" in doctor_name else doctor_name

    branches = settings.get("branches", [])
    appt_cfg = settings.get("appointment_config", {})
    schedules = appt_cfg.get("schedule", {}) if isinstance(appt_cfg, dict) else {}

    parsed_schedules = {}
    for b in branches:
        b_id = b.get("id")
        b_name = b.get("name", "Clinic").strip()
        b_sched = schedules.get(b_id, {})
        day_map = {}
        for idx, day_k in enumerate(DAY_KEYS):
            slots = b_sched.get(day_k, [])
            valid_slots = []
            if isinstance(slots, list):
                for s in slots:
                    if isinstance(s, dict):
                        st = _parse_time_str(s.get("start", ""))
                        et = _parse_time_str(s.get("end", ""))
                        if st and et and st < et:
                            valid_slots.append((st, et))
            day_map[idx] = valid_slots
        parsed_schedules[b_name] = day_map

    open_now_branches = []
    upcoming_today_branches = []
    closed_today_branches = []

    for b_name, day_map in parsed_schedules.items():
        slots = day_map.get(current_day_idx, [])
        for start, end in slots:
            if start <= now_time < end:
                open_now_branches.append((b_name, start, end))
            elif now_time < start:
                upcoming_today_branches.append((b_name, start, end))
            else:
                closed_today_branches.append((b_name, start, end))

    if open_now_branches:
        status_line = "OPEN NOW (" + "; ".join(f"{b} until {_format_time_natural_dt(end)}" for b, _, end in open_now_branches) + ")"
        b_name, _, end_t = open_now_branches[0]
        immediate_answer = f"{doc_display} is available right now today at {b_name} until {_format_time_natural_dt(end_t)}."
    elif upcoming_today_branches:
        b_name, start_t, end_t = upcoming_today_branches[0]
        status_line = f"OPENS TODAY at {_format_time_natural_dt(start_t)} ({b_name})"
        immediate_answer = f"{doc_display} will be available today at {b_name} from {_format_time_natural_dt(start_t)} to {_format_time_natural_dt(end_t)}."
    else:
        next_slot_info = None
        for days_ahead in range(1, 8):
            next_day_idx = (current_day_idx + days_ahead) % 7
            next_day_name = DAY_NAMES[next_day_idx]
            for b_name, day_map in parsed_schedules.items():
                slots = day_map.get(next_day_idx, [])
                if slots:
                    start_t, end_t = slots[0]
                    next_slot_info = (next_day_name, days_ahead, b_name, start_t, end_t)
                    break
            if next_slot_info:
                break

        if closed_today_branches:
            latest_end = max(end for _, _, end in closed_today_branches)
            status_line = f"CLOSED FOR TODAY (Closed at {_format_time_natural_dt(latest_end)})"
        else:
            status_line = f"CLOSED TODAY ({current_day_name})"

        if next_slot_info:
            n_day, days_ahead, n_branch, n_start, n_end = next_slot_info
            day_ref = "tomorrow" if days_ahead == 1 else f"this coming {n_day}"
            immediate_answer = f"The clinic is currently closed. {doc_display} will next be available {day_ref} ({n_day}) from {_format_time_natural_dt(n_start)} to {_format_time_natural_dt(n_end)} at {n_branch}."
        else:
            immediate_answer = "The clinic is currently closed. Please contact our reception desk."

    tomorrow_idx = (current_day_idx + 1) % 7
    tomorrow_name = DAY_NAMES[tomorrow_idx]
    tomorrow_open = []
    for b_name, day_map in parsed_schedules.items():
        slots = day_map.get(tomorrow_idx, [])
        if slots:
            slot_str = " & ".join(f"{_format_time_natural_dt(s)} to {_format_time_natural_dt(e)}" for s, e in slots)
            tomorrow_open.append(f"{b_name}: {slot_str}")

    tomorrow_summary = "; ".join(tomorrow_open) if tomorrow_open else "Closed all day"

    day_ref_lines = []
    for d_idx, d_name in enumerate(DAY_NAMES):
        day_branch_parts = []
        for b_name, day_map in parsed_schedules.items():
            slots = day_map.get(d_idx, [])
            if slots:
                slot_str = " & ".join(f"{_format_time_natural_dt(s)} to {_format_time_natural_dt(e)}" for s, e in slots)
                day_branch_parts.append(f"{b_name} ({slot_str})")
        if day_branch_parts:
            day_ref_lines.append(f"  * {d_name}: " + " & ".join(day_branch_parts))
        else:
            day_ref_lines.append(f"  * {d_name}: Closed all day")

    day_ref_str = "\n".join(day_ref_lines)

    return (
        "## LIVE CLINIC STATUS & DOCTOR AVAILABILITY (IST)\n"
        f"- Live Timestamp: {current_day_name}, {current_date_str} at {current_time_str} IST\n"
        f"- Current Operating Status: {status_line}\n"
        f"- Direct Availability Fact: {immediate_answer}\n"
        f"- Tomorrow's Availability ({tomorrow_name}): {tomorrow_summary}\n"
        "- Weekly Consultation Schedule Reference (Use when caller asks about a specific day or branch):\n"
        f"{day_ref_str}"
    )

def _format_time_natural_dt(t: dtime) -> str:
    h = t.hour % 12 or 12
    ampm = "AM" if t.hour < 12 else "PM"
    if t.minute == 0:
        return f"{h} {ampm}"
    return f"{h}:{t.minute:02d} {ampm}"


def _format_time_natural(t: str) -> str:
    """Convert '10:00' to '10 AM', '19:00' to '7 PM', '14:30' to '2:30 PM'."""
    try:
        parts = t.split(":")
        h = int(parts[0])
        m = int(parts[1])
        ampm = "AM" if h < 12 else "PM"
        h12 = h % 12 or 12
        if m == 0:
            return f"{h12} {ampm}"
        return f"{h12}:{m:02d} {ampm}"
    except Exception:
        return t


def format_branch_schedule(sched: Optional[Dict[str, Any]]) -> str:
    """Format weekly branch schedule into a compact, natural readable string."""
    if not sched or not isinstance(sched, dict):
        return "Monday to Friday: 10 AM to 7 PM (Closed Weekends)"

    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    day_names = {
        "monday": "Monday",
        "tuesday": "Tuesday",
        "wednesday": "Wednesday",
        "thursday": "Thursday",
        "friday": "Friday",
        "saturday": "Saturday",
        "sunday": "Sunday",
    }

    chunks_by_day = {}
    for d in days:
        chunks = sched.get(d, [])
        if chunks and isinstance(chunks, list):
            chunk_strs = [
                f"{_format_time_natural(c.get('start', ''))} to {_format_time_natural(c.get('end', ''))}"
                for c in chunks
                if c.get("start") and c.get("end")
            ]
            chunks_by_day[d] = " & ".join(chunk_strs) if chunk_strs else "Closed"
        else:
            chunks_by_day[d] = "Closed"

    # Check if Mon-Fri are identical and weekends are closed
    weekday_chunks = [chunks_by_day[d] for d in days[:5]]
    if (
        len(set(weekday_chunks)) == 1
        and weekday_chunks[0] != "Closed"
        and chunks_by_day["saturday"] == "Closed"
        and chunks_by_day["sunday"] == "Closed"
    ):
        return f"Monday to Friday: {weekday_chunks[0]} (Closed Weekends)"

    open_days = []
    for d in days:
        if chunks_by_day[d] != "Closed":
            open_days.append(f"{day_names[d]}: {chunks_by_day[d]}")

    if not open_days:
        return "Temporarily Closed"

    return "; ".join(open_days)


def _format_time_standard(t: str) -> str:
    """Convert '09:00' to '9:00 AM', '19:00' to '7:00 PM', '14:30' to '2:30 PM'."""
    try:
        parts = t.split(":")
        h = int(parts[0])
        m = int(parts[1])
        ampm = "AM" if h < 12 else "PM"
        h12 = h % 12 or 12
        return f"{h12}:{m:02d} {ampm}"
    except Exception:
        return t


def format_schedule_for_template(sched: Optional[Dict[str, Any]], max_len: int = 80) -> str:
    """
    Format weekly branch schedule into the exact textual format required for
    the clinic_and_appointment_details WhatsApp template.
    Guarantees the parameter stays compact to respect Meta's 1024-character total limit.
    e.g., 'Monday to Friday: 9:00 AM to 7:00 PM'
    or 'Thu: 2:00 PM to 6:00 PM; Fri: 9:00 AM to 7:00 PM; Sat: 11:00 AM to 3:00 PM'
    """
    if not sched or not isinstance(sched, dict):
        return "Monday to Friday: 9:00 AM to 7:00 PM"

    days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    full_day_labels = {
        "monday": "Monday", "tuesday": "Tuesday", "wednesday": "Wednesday",
        "thursday": "Thursday", "friday": "Friday", "saturday": "Saturday", "sunday": "Sunday"
    }
    short_day_labels = {
        "monday": "Mon", "tuesday": "Tue", "wednesday": "Wed",
        "thursday": "Thu", "friday": "Fri", "saturday": "Sat", "sunday": "Sun"
    }

    def build_text(labels: dict, sep_range: str, sep_slots: str) -> str:
        day_summaries = {}
        for d in days:
            slots = sched.get(d, [])
            if not slots or not isinstance(slots, list):
                day_summaries[d] = "Closed"
            else:
                slot_strs = [
                    f"{_format_time_standard(s.get('start', ''))}{sep_slots}{_format_time_standard(s.get('end', ''))}"
                    for s in slots
                    if s.get("start") and s.get("end")
                ]
                day_summaries[d] = " & ".join(slot_strs) if slot_strs else "Closed"

        groups = []
        current_days = [days[0]]
        current_summary = day_summaries[days[0]]

        for d in days[1:]:
            if day_summaries[d] == current_summary:
                current_days.append(d)
            else:
                groups.append((current_days, current_summary))
                current_days = [d]
                current_summary = day_summaries[d]
        groups.append((current_days, current_summary))

        open_groups = [(ds, s) for ds, s in groups if s != "Closed"]
        if not open_groups:
            return "Temporarily Closed"

        parts = []
        for ds, summary in groups:
            if summary == "Closed":
                continue
            if len(ds) == 1:
                day_range = labels[ds[0]]
            elif len(ds) == 2:
                day_range = f"{labels[ds[0]]} & {labels[ds[1]]}"
            else:
                day_range = f"{labels[ds[0]]}{sep_range}{labels[ds[-1]]}"
            parts.append(f"{day_range}: {summary}")

        return "; ".join(parts)

    # 1. Try full natural format (e.g. 'Monday to Friday: 9:00 AM to 7:00 PM')
    res_full = build_text(full_day_labels, " to ", " to ")
    if len(res_full) <= max_len:
        return res_full

    # 2. Try compact format (e.g. 'Thu: 2:00 PM to 6:00 PM; Fri: 9:00 AM to 7:00 PM; Sat: 11:00 AM to 3:00 PM')
    res_compact = build_text(short_day_labels, " - ", " to ")
    if len(res_compact) <= max_len:
        return res_compact

    # 3. Tight format with hyphens
    res_tight = build_text(short_day_labels, "-", "-")
    if len(res_tight) <= max_len:
        return res_tight

    return res_tight[:max_len-3] + "..."



def compile_unified_prompt(settings: Optional[Dict[str, Any]] = None) -> str:
    """
    Compiles compact voice agent prompt with branch operating hours,
    friendly and eager persona (not appointment-pushing), strict 2-sentence brevity,
    strict language lock, proactive WhatsApp dispatch, reliable call ending, and guardrails.
    """
    cfg = dict(DEFAULT_CLINIC_SETTINGS)
    if settings:
        cfg.update(settings)

    clinic_name = cfg.get("clinic_name", "Aakruti Aesthetics & Plastic Surgery Clinic").strip()
    doctor_name = cfg.get("doctor_name", "Doctor Kaushal Priya Anand").strip()
    doctor_credentials = cfg.get("doctor_credentials", "M.B.B.S, M.S, M.Ch Plastic Surgery, 20+ years of excellence").strip()
    reception = cfg.get("official_reception", "+91 90020 08137 / +91 90020 08147").strip()
    email = cfg.get("email", "akrutiaestheticsurgery@gmail.com").strip()
    procedures = cfg.get("procedures", "").strip()

    branches = cfg.get("branches", [])
    appointment_config = cfg.get("appointment_config", {})
    schedules = appointment_config.get("schedule", {}) if isinstance(appointment_config, dict) else {}

    branch_lines = []
    for b in branches:
        b_name = b.get("name", "Clinic").strip()
        b_addr = b.get("address", "").strip()
        branch_lines.append(f"- {b_name}: {b_addr}")

    branches_str = "\n".join(branch_lines) if branch_lines else "- Clinic Branches: Durgapur Clinic and Burdwan Clinic"

    prompt = f"""## IDENTITY, ROLE & TONE
You are a warm, genuinely friendly, and attentive front-desk receptionist at {clinic_name}.
- Natural Conversational Variety: Answer caller questions directly and naturally. NEVER repeat the same robotic opener (DO NOT start every reply with "हाँ बिल्कुल!", "অবশ্যই!", or "Certainly!"). Speak with natural variety.
- Eager to Help: Show cheerful warmth and genuine enthusiasm to help callers explore their cosmetic and treatment questions. You love guiding patients!
- Not an Appointment-Pusher: Do NOT rush or push callers to book an appointment. First happily answer their questions, explain what Doctor Anand offers, and make them feel supported.
- Brevity Limit: Keep every reply to MAXIMUM 1 to 2 short sentences at a time. Sound lively, natural, and conversational without rambling.

## GREETING (Say verbatim on call start):
"नमस्ते! Welcome to {clinic_name}. ... Aap kis language me baat karna prefer karenge? ... Hindi, Bengali, ya English?"

## LANGUAGE LOCK (ABSOLUTE & UNBREAKABLE)
- Once the caller speaks or selects a language (Bengali, Hindi, or English), you MUST speak in that language for 100% of your responses throughout the entire call.
- NEVER switch back to English when the caller is speaking Hindi or Bengali.
- State all consultation timings, doctor availability, operating days, and clinic information dynamically in the caller's active language (Hindi / Bengali / English). Do NOT switch to English when quoting schedules or hours on Hindi/Bengali calls.
- Only switch languages if the caller explicitly asks or starts speaking in another language.
- Bengali: 100% Bengali in Bangla script (বাংলা লিপি).
- Hindi: 100% Hindi in Devanagari script (देवनागरी).
- English: Natural English.

## CLINIC GROUND TRUTH & LOCATIONS
- Clinic: {clinic_name}
- Chief Surgeon: {doctor_name} ({doctor_credentials})
- Reception: {reception} | Email: {email}
- Clinic Locations:
{branches_str}
- Services: {procedures}

## PROCEDURES & CONSULTATIVE GUIDANCE
- When a caller asks about a procedure or aesthetic goal, warmly reassure them that {doctor_name} has extensive experience performing it at {clinic_name}.
- Answer their specific query clearly and ask a friendly, supportive follow-up question, keeping within 2 sentences max.

## APPOINTMENTS & TIMINGS POLICY (USE LIVE AVAILABILITY SECTION)
- Reference Live Availability: Always use the `## LIVE CLINIC STATUS & DOCTOR AVAILABILITY (IST)` section for doctor availability, current open status, and consultation hours.
- Dynamic Language Translation: State the availability facts and timings naturally in the caller's active conversation language (Hindi / Bengali / English).
- Conversational Timings (DO NOT DUMP ENTIRE SCHEDULE):
  - When asked when the doctor is available or about clinic hours: State the current availability fact from the live availability section in 1 short sentence.
  - When asked about a specific day or specific branch: Refer to that specific day/branch from the schedule reference.
- Booking Policy (Strict - No Phone Bookings):
  - NEVER book or schedule appointments over the phone yourself.
  - Inform the caller politely that consultations with Doctor Anand are scheduled directly by calling our clinic reception desk, and offer to send clinic details and reception numbers to their WhatsApp.

## WHATSAPP DTMF NUMBER COLLECTION (STRICT 2 PHASES)
Phase 1 - Request Keypad Entry:
- Whenever you offer WhatsApp details or the caller agrees/asks to receive WhatsApp details (e.g., "Yes", "পাঠিয়ে দিন", "দেুম", "हाँ भेज दीजिए", "sure", "okay", "send it"):
- You DO NOT have the number yet! DO NOT say "I noted your number" or "আমি নম্বর নিয়েছি".
- You MUST explicitly ask them to type their 10-digit number on their phone keypad:
  * Bengali: "অনুগ্রহ করে আপনার ফোনের কিপ্যাডে আপনার ১০ সংখ্যার হোয়াটসঅ্যাপ নম্বরটি টাইপ করুন।"
  * Hindi: "कृपया अपने फोन के कीपैड पर अपना 10 अंकों का व्हाट्सएप नंबर टाइप करें।"
  * English: "Please enter your 10-digit WhatsApp number on your phone keypad."

Phase 2 - Confirmation After Digits:
- ONLY AFTER you see `[Keypad Input Received: ...]` in the transcript or if the caller enters/speaks digits:
- Confirm warmly in 1 short sentence:
  * Bengali: "ধন্যবাদ! আমি এখনই হোয়াটসঅ্যাপে সমস্ত বিবরণ পাঠিয়ে দিচ্ছি।"
  * Hindi: "धन्यवाद! मैं अभी व्हाट्सएप पर सभी विवरण भेज रही हूँ।"
  * English: "Thank you! I am sending all the details to your WhatsApp right now."

## ENDING THE CALL & IMMEDIATE HANGUP (CRITICAL)
Whenever the caller says goodbye, thank you, thanks, is done, is busy, called by mistake, or indicates conclusion (e.g. 'থ্যাঙ্ক ইউ', 'thank you', 'thanks', 'ধন্যবাদ', 'ঠিক আছে থ্যাঙ্ক ইউ', 'bye', 'বিদায়', 'রেখে দিন', 'কাটছি', 'अलविदा', 'शुक्रिया', 'wrong number', 'busy'):
You MUST IMMEDIATELY call the `end_call` tool to disconnect the phone call.

## GUARDRAILS
- Clinic Domain Only: Strictly decline any non-clinic queries.
- Safety: Never prescribe medicines or guarantee surgical results. Recommend in-person consultation.

## TTS RULES
- ALWAYS write "Doctor" / "ডাক্তার" / "डॉक्टर" (never Dr. or ডা.).
- Speak natural times in the active language: e.g., "সকাল ১০ টা থেকে সন্ধ্যা ৭ টা", "सुबह 10 बजे से शाम 7 बजे तक", "10 AM to 7 PM"."""

    return prompt.strip()
