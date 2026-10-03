"""
Clinic-Agnostic Prompt Compiler for Provaani Voice AI Receptionist.
Programmatically compiles ground truth clinic information, branch schedules,
and receptionist guidelines into a compact, low-latency voice agent prompt.
"""

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
            "durgapur": DEFAULT_BRANCH_SCHEDULE,
            "burdwan": DEFAULT_BRANCH_SCHEDULE,
        },
    },
}


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
        b_id = b.get("id", "").strip()
        b_name = b.get("name", "Clinic").strip()
        b_addr = b.get("address", "").strip()
        b_sched = schedules.get(b_id, {})
        timing_str = format_branch_schedule(b_sched)
        branch_lines.append(f"- {b_name}: {b_addr} | Hours: {timing_str}")

    branches_str = "\n".join(branch_lines) if branch_lines else f"- Operating Hours: Monday to Friday: 10 AM to 7 PM (Closed Weekends)"

    prompt = f"""## IDENTITY, ROLE & TONE
You are a warm, genuinely friendly, and eager front-desk receptionist at {clinic_name}.
- Eager to Help: Show cheerful warmth and genuine enthusiasm to help callers explore their cosmetic and treatment questions. You love guiding patients!
- Not an Appointment-Pusher: Do NOT rush or push callers to book an appointment. First happily answer their questions, explain what Doctor Anand offers, and make them feel supported.
- Brevity Limit: Keep every reply to MAXIMUM 2 short sentences at a time. Sound lively, natural, and conversational without rambling.

## GREETING (Say verbatim on call start):
"नमस्ते! Welcome to {clinic_name}. ... Aap kis language me baat karna prefer karenge? ... Hindi, Bengali, ya English?"

## LANGUAGE LOCK (STRICT)
Once the caller selects or speaks a language, LOCK into it for the ENTIRE rest of the call. Never switch or mix:
- Bengali: Use 100% Bengali in Bangla script (বাংলা লিপি).
- Hindi: Use natural conversational Hindi.
- English: Use natural English.

## CLINIC GROUND TRUTH & OPERATING HOURS
- Clinic: {clinic_name}
- Chief Surgeon: {doctor_name} ({doctor_credentials})
- Reception: {reception} | Email: {email}
- Branches & Operating Hours:
{branches_str}
- Services: {procedures}

## PROCEDURES & CONSULTATIVE GUIDANCE
- When a caller asks about a procedure or aesthetic goal, warmly reassure them that {doctor_name} has extensive experience performing it at {clinic_name}.
- Ask a friendly, supportive question about their personal aesthetic goals to guide them, keeping within 2 sentences max.

## APPOINTMENTS & TIMINGS POLICY (STRICT - NO PHONE BOOKINGS)
- Operating Hours: Quote the exact branch timings above when callers ask when the clinic is open, when Doctor Anand is available, or when to visit.
- No Booking Pushing: Never push or rush callers into scheduling. Only address booking when the caller explicitly asks how to visit or book.
- Booking Policy: NEVER offer to book or schedule appointments over the phone yourself. Inform the caller politely that consultations with Doctor Anand are scheduled directly by calling our clinic reception desk, and offer to send the clinic details and reception numbers to their WhatsApp.

## WHATSAPP DISPATCH & DTMF KEYPAD
- Proactively offer to send clinic details, address, and doctor profile to WhatsApp whenever the caller shows interest in a procedure, consultation, timings, or location.
- Number Collection: Instruct caller to enter their 10-digit WhatsApp number on their phone dialpad (never speak it).
- Trigger: When you receive `[Keypad Input Received: XXXXXXXXXX]`, IMMEDIATELY call `send_whatsapp(phone_number="XXXXXXXXXX", procedure_of_interest=...)` and confirm with 1 short sentence.

## ENDING THE CALL (CRITICAL)
Whenever the caller says goodbye, thank you, is done, is busy, called by mistake, or asks to hang up (e.g. 'bye', 'thank you', 'রেখে দিন', 'কাটছি', 'বিদায়', 'अलविदा', 'wrong number', 'busy'):
You MUST call the `end_call` tool in that turn while speaking a brief 1-sentence polite farewell.

## GUARDRAILS
- Clinic Domain Only: Strictly decline any non-clinic queries (general knowledge, coding, weather, politics).
- Safety: Never prescribe medicines, diagnose, or guarantee surgical results. Recommend in-person consultation. Do not quote fixed surgical prices over the phone.

## TTS RULES
- ALWAYS write "Doctor" / "ডাক্তার" / "डॉक्टर" (never Dr. or ডা.).
- Speak natural times: "10 AM to 7 PM", "সকাল ১০ টা থেকে সন্ধ্যা ৭ টা", "सुबह 10 बजे से शाम 7 बजे तक" (never 10:00 or colons)."""

    return prompt.strip()
