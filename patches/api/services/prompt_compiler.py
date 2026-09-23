"""
Clinic-Agnostic Prompt Compiler for Provaani Voice AI Receptionist.
Programmatically compiles ground truth clinic information, procedures,
and weekly appointment schedules into a unified voice agent prompt.
Zero clinic-specific strings or schedules are hardcoded.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

BOOK_APPOINTMENT_TOOL_UUID = "c84e1234-5678-4321-9876-abcdef012345"

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
            "landmark": "Near City Centre",
            "phone": "+91 90020 08137",
        },
        {
            "id": "burdwan",
            "name": "Burdwan Clinic",
            "address": "S. S. Doctor Centre, Power House Para, Near Park Nursing Home, Burdwan",
            "landmark": "Near Park Nursing Home",
            "phone": "+91 90020 08147",
        },
    ],
    "procedures": (
        "Head & Face: Facelift, Asian Eyelid Blepharoplasty, Dimpleplasty, Buccal Fat Pad Removal, Rhinoplasty, Lip Augmentation & Reduction, Chin Augmentation, Ear Reconstruction.\n"
        "Breast Surgery: Breast Augmentation, Breast Reduction, Breast Lift, Gynaecomastia Surgery.\n"
        "Tummy & Body Contouring: Liposuction, Tummy Tuck (Abdominoplasty), Mini Tummy Tuck, 6-pack Abs, Arm Lift, Thigh Lift, Fat Grafting, Buttock Contouring.\n"
        "Skin Treatments: Acne & Acne Scars, Chemical Peels, Micro Needling, Mole Excision, Botox & Fillers, Medical Facial, Cryolipolysis.\n"
        "Hair Treatments: Hair Transplant, PRP (Platelet-Rich Plasma), Eyebrow Transplant, Beard & Moustache Transplant, Scalp & Eyebrow Micropigmentation.\n"
        "Reconstructive & Trauma: Burns & Burn Deformities, Maxillofacial Surgery, Trauma & Replantation."
    ),
    "special_notes": "All consultations require appointment confirmation directly with clinic reception.",
    "appointment_config": {
        "enabled": True,
        "allow_booking": True,
        "schedule": {
            "durgapur": {
                "monday": [{"start": "10:00", "end": "14:00"}, {"start": "17:00", "end": "20:00"}],
                "tuesday": [{"start": "16:00", "end": "19:00"}],
                "wednesday": [{"start": "10:00", "end": "14:00"}, {"start": "17:00", "end": "20:00"}],
                "thursday": [{"start": "10:00", "end": "14:00"}, {"start": "17:00", "end": "20:00"}],
                "friday": [{"start": "10:00", "end": "14:00"}, {"start": "17:00", "end": "20:00"}],
                "saturday": [],
                "sunday": [],
            },
            "burdwan": {
                "monday": [],
                "tuesday": [],
                "wednesday": [],
                "thursday": [{"start": "14:00", "end": "18:00"}],
                "friday": [],
                "saturday": [{"start": "11:00", "end": "15:00"}],
                "sunday": [],
            },
        },
    },
}

DAYS_ORDER = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _format_time_label(hh_mm: str) -> str:
    """Format 24-hr '09:00' to 12-hr natural string '9 AM' or '14:30' to '2:30 PM'."""
    try:
        parts = hh_mm.split(":")
        hour = int(parts[0])
        minute = int(parts[1])
        suffix = "AM" if hour < 12 else "PM"
        display_hour = hour % 12
        if display_hour == 0:
            display_hour = 12
        if minute == 0:
            return f"{display_hour} {suffix}"
        return f"{display_hour}:{minute:02d} {suffix}"
    except Exception:
        return hh_mm


def format_clinic_ground_truth(settings: Dict[str, Any]) -> str:
    clinic_name = settings.get("clinic_name", "Clinic").strip()
    doctor_name = settings.get("doctor_name", "Doctor").strip()
    doctor_credentials = settings.get("doctor_credentials", "").strip()
    reception = settings.get("official_reception", "").strip()
    email = settings.get("email", "").strip()
    notes = settings.get("special_notes", "").strip()
    branches = settings.get("branches", [])

    lines = [
        f"- Clinic Name: {clinic_name}",
        f"- Chief Doctor: {doctor_name}" + (f" ({doctor_credentials})" if doctor_credentials else ""),
    ]

    if reception:
        lines.append(f"- Official Reception & Contact Numbers: {reception}")
    if email:
        lines.append(f"- Official Email: {email}")

    for idx, b in enumerate(branches, start=1):
        b_name = b.get("name", f"Branch {idx}").strip()
        b_id = b.get("id", f"branch_{idx}").strip()
        b_addr = b.get("address", "").strip()
        b_landmark = b.get("landmark", "").strip()
        b_phone = b.get("phone", "").strip()

        addr_str = b_addr
        if b_landmark:
            addr_str += f" (Landmark: {b_landmark})"
        if b_phone:
            addr_str += f" [Contact: {b_phone}]"

        lines.append(f"- {b_name} [ID: '{b_id}']: {addr_str}")

    if notes:
        lines.append(f"- Practice Notes & Guidelines: {notes}")

    return "\n".join(lines)


def format_appointment_policy(settings: Dict[str, Any]) -> str:
    appt_config = settings.get("appointment_config", {})
    # Main Toggle: Whether the voice agent discusses appointment timings & schedules
    timings_enabled = bool(appt_config.get("enabled", False))
    # Sub Toggle: Whether the voice agent can autonomously book appointments
    allow_booking = bool(appt_config.get("allow_booking", True)) if timings_enabled else False
    
    doctor_name = settings.get("doctor_name", "the doctor").strip()
    reception = settings.get("official_reception", "our clinic reception").strip()
    branches = settings.get("branches", [])
    schedule_map = appt_config.get("schedule", {})

    # Common WhatsApp DTMF Collection & Dispatch Rule for All Modes
    whatsapp_dispatch_rule = """
## WHATSAPP DISPATCH & DTMF KEYPAD COLLECTION RULES:
- When the caller asks to receive clinic details, addresses, doctor information, or appointment details on WhatsApp:
  1. ALWAYS instruct the caller to enter their 10-digit WhatsApp number on their phone dialpad (NEVER ask them to speak it aloud):
     - Bengali: "দয়া করে ফোনের ডায়ালপ্যাডে আপনার ১০ সংখ্যার হোয়াটসঅ্যাপ নম্বরটি টাইপ করুন।"
     - Hindi: "कृपया फ़ोन के डायलपैড पर अपने 10 अंकों का WhatsApp नंबर टाइप करें।"
     - English: "Please enter your 10-digit WhatsApp number on your phone keypad."
  2. When you receive `[Keypad Input Received: XXXXXXXXXX]` (or 10 digits entered via keypad):
     - IMMEDIATELY call the `send_whatsapp` tool with `phone_number`.
     - Then say 1 brief confirmation sentence (e.g. "আমি আপনার হোয়াটসঅ্যাপে ক্লিনিকের সব বিবরণ পাঠিয়ে দিয়েছি।" / "मैंने आपके WhatsApp पर डिटेल्स भेज दी हैं।" / "I have sent the clinic details to your WhatsApp.").
"""

    # CASE 1: Main Toggle is OFF (Information Only Mode)
    # The agent provides general practice info (doctor, procedures, contact), but does NOT discuss or give clinic schedule/timings.
    if not timings_enabled:
        return f"""## CLINIC INQUIRIES & APPOINTMENT POLICY (GENERAL INFORMATION MODE):
- You provide general information about the clinic, doctor qualifications, procedures, and official contact details.
- Do NOT quote specific consultation hours or appointment time slots.
- If a caller asks about appointment booking or doctor timings, politely inform them:
  "Our appointments and consultation schedules are managed directly by our clinic reception team at {reception}. Please call our reception desk directly for available timings and appointments."
- Offer to send the clinic addresses and reception numbers to their WhatsApp.
{whatsapp_dispatch_rule}"""

    # Date Anchor for Timings & Booking
    try:
        now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))
    except Exception:
        now_ist = datetime.now()

    date_str = now_ist.strftime("%A, %B %d, %Y")
    time_str = now_ist.strftime("%I:%M %p IST")

    # Generate strict JSON schedule covering every day of the week for every branch
    schedule_json_obj = {}
    for b in branches:
        b_id = b.get("id", "").strip()
        b_name = b.get("name", "Main Branch").strip()
        b_schedule = schedule_map.get(b_id, {})

        branch_weekly = {}
        for day in DAYS_ORDER:
            day_cap = day.capitalize()
            chunks = b_schedule.get(day, [])
            if chunks and isinstance(chunks, list):
                time_strs = []
                for c in chunks:
                    st = _format_time_label(c.get("start", ""))
                    et = _format_time_label(c.get("end", ""))
                    if st and et:
                        time_strs.append(f"{st} to {et}")
                branch_weekly[day_cap] = time_strs if time_strs else "Closed"
            else:
                branch_weekly[day_cap] = "Closed"

        schedule_json_obj[b_id] = {
            "branch_name": b_name,
            "weekly_consultation_schedule": branch_weekly,
        }

    branch_schedule_json_str = json.dumps(schedule_json_obj, indent=2)
    branch_count = len(branches)
    multi_branch_instruction = (
        "2. If the caller asks for an appointment or consultation hours, ask which clinic location is most convenient for them.\n"
        if branch_count > 1
        else "2. Inquire what day and time of day they would like to visit for their consultation.\n"
    )

    sample_branch_id = branches[0].get("id", "main") if branches else "main"

    # Realtime Dynamic Date Anchor (Evaluated on every call by the engine's template renderer)
    date_anchor_block = """## CURRENT DATE & TIME ANCHOR:
- Today's Day of the Week: {{current_weekday_Asia/Kolkata}}
- Current Date & Time: {{current_time_Asia/Kolkata}}
- Timezone: Asia/Kolkata (Indian Standard Time)
- CRITICAL: Always use the exact day name from 'Today's Day of the Week' above to identify what day today is."""

    # CASE 2: Timings ON, but Autonomous Booking is OFF (Timings Sharing & Referral Mode)
    if not allow_booking:
        return f"""{date_anchor_block}

## CLINIC OPERATING HOURS & APPOINTMENT TIMINGS (RECEPTION REFERRAL MODE):
```json
{branch_schedule_json_str}
```

- SCHEDULING & TIMING RULES:
  1. DOCTOR AVAILABILITY IS ONLY BY APPOINTMENT: When a caller asks if the doctor is sitting, available, or open today or on any day, look up that exact branch and day in the JSON schedule above.
  2. Direct appointment booking is DISABLED on this voice agent. Never confirm or book an appointment autonomously.
  3. Inform the caller politely:
     "Our doctor is available at [Branch] on [Days and Hours]. To book your consultation slot, please call our clinic reception directly at {reception}."
{whatsapp_dispatch_rule}"""

    # CASE 3: Timings ON AND Autonomous Booking is ON (Active Booking Mode)
    return f"""{date_anchor_block}

## APPOINTMENT CONSULTATION SCHEDULE (STRICT JSON SPECIFICATION):
The following JSON defines the EXACT and ONLY available consultation timings for Doctor {doctor_name}. Every day of the week is explicitly defined as either open time slots or \"Closed\":
```json
{branch_schedule_json_str}
```

- STRICT SCHEDULING & BOOKING INSTRUCTIONS:
  1. STRICT BRANCH & DAY LOOKUP (ZERO CROSS-CONTAMINATION):
     - First determine the requested branch: 'durgapur' or 'burdwan'.
     - ONLY look under that specific branch in the JSON schedule above. NEVER quote or offer days/hours from another branch.
     - When the caller asks about 'today', look up the exact day from 'Today's Day of the Week' ({{{{current_weekday_Asia/Kolkata}}}}) under that branch.
     - If the day says \"Closed\" in the JSON: Tell the caller that branch is closed on that day. Look up the open days under that SAME branch and offer them. NEVER invent open days.
  {multi_branch_instruction}
  3. Ask what day and approximate time they prefer to visit.
  4. STRICT TIME WINDOW ENFORCEMENT:
     - Check if the requested day has active consultation hours at that clinic branch in the JSON.
     - Check if the requested time falls strictly BETWEEN the start and end of an open session.
     - IF OUTSIDE OPEN HOURS or on a CLOSED DAY: Politely inform the caller that {doctor_name} is unavailable at that time, explain when that branch is open, and offer the nearest open day/time window from that branch's JSON. NEVER book outside designated clinic hours.
  5. CONFIRM CALLER DETAILS & DEDICATED DTMF KEYPAD COLLECTION:
     - Ask for the patient's full name.
     - To ensure 100% accuracy, explicitly ask the caller to use their phone dialpad:
       "Could you please enter your 10-digit mobile number on your phone's dialpad or keypad?"
     - DTMF KEYPAD HANDLING:
       * When the user types on their phone keypad, a `[Keypad Input Received: XXXXXXXXXX]` message will appear in the conversation.
       * Always use this exact 10-digit keypad number for booking.
     - SPOKEN NUMBER SAFEGUARDS (ZERO GUESSING):
       * If the caller speaks their number instead of typing it, you MUST verify it contains exactly 10 digits.
       * NEVER invent, guess, or pad missing digits (e.g. if they say 8 digits, NEVER add zeroes).
       * If fewer or more than 10 digits are received, ask:
         "I only received [count] digits. Please enter your 10-digit mobile number on your phone's dialpad."
  6. EXECUTE `book_appointment` TOOL:
     - Once the patient agrees to an available consultation window within open clinic hours, IMMEDIATELY call the `book_appointment` tool:
       * `patient_name`: Full name of caller/patient
       * `phone_number`: Confirmed 10-digit mobile number
       * `branch_id`: Chosen branch ID (e.g. '{sample_branch_id}')
       * `appointment_date`: Date in YYYY-MM-DD format
       * `appointment_time`: Consultation time (e.g. '03:30 PM')
       * `procedure_of_interest`: Procedure or treatment discussed
  7. AFTER TOOL EXECUTION:
     - If booking succeeds: Speak a warm 1-sentence confirmation:
       "Your consultation with {doctor_name} has been confirmed for [Day, Date] at [Time] at our [Branch] clinic, and confirmation details have been sent to your WhatsApp. We look forward to seeing you!"
     - If booking is rejected: Explain the reason politely and offer an alternate open time."""



def compile_unified_prompt(settings: Dict[str, Any]) -> str:
    """
    Compiles full clinic-agnostic voice agent system prompt from configuration dictionary.
    """
    clinic_name = settings.get("clinic_name", "our clinic").strip()
    doctor_name = settings.get("doctor_name", "our specialist doctor").strip()
    procedures = settings.get("procedures", "").strip()

    clinic_facts_block = format_clinic_ground_truth(settings)
    appointment_block = format_appointment_policy(settings)

    prompt = f"""## OPENING GREETING (Say this exact phrase on call start):
"नमस्ते! Welcome to {clinic_name}. ... Aap kis language me baat karna prefer karenge? ... Hindi, Bengali, ya English?"

## LANGUAGE HANDLING:
- If caller chooses BENGALI (or speaks Bengali): Reply warmly in pure Bangla ("খুব ভালো! বলুন, আপনাকে কীভাবে সাহায্য করতে পারি?") and lock strictly into 100% Bengali in Bangla script (বাংলা লিপি) for the entire call.
- If caller chooses HINDI (or speaks Hindi): Reply warmly in Hindi ("बहुत बढ़िया! बताइए, मैं आपकी क्या help कर सकती हूँ?") and lock into conversational Hindi.
- If caller chooses ENGLISH (or speaks English): Reply warmly in English ("Great! How can I help you today?") and lock into English.

## AUTHENTIC CLINIC FACTS (GROUND TRUTH ONLY — NEVER INVENT ANY DETAILS):
{clinic_facts_block}

## PROCEDURES & SERVICES OFFERED:
{procedures}

## NATURAL CONVERSATIONAL STYLE & INQUIRIES (NO TEXTBOOK DEFINITIONS):
- When a caller mentions a procedure or treatment:
  - Do NOT give a dry textbook definition or clinical lecture.
  - Instead, respond warmly and conversationally as an experienced clinic assistant. Acknowledge that {doctor_name} performs this procedure regularly, and ask a relevant, consultative follow-up question.
  - ONLY define the procedure if the caller explicitly asks "What does this procedure mean?" or "How is it done?".

{appointment_block}

## STRICT TIME & NUMBER PRONUNCIATION (CRITICAL FOR NATURAL SPEECH):
- NEVER write times with colons and double zeroes (NEVER write '9:00', '6:00', '7:00', '09:00', '19:00').
- NEVER write concatenated time numbers. ALWAYS insert punctuation (commas, periods) and spaces for natural breathing pauses.
- Exact language rules:
  - English: Write "9 AM to 7 PM", "6 PM", "7 PM", "2:30 PM".
  - Bengali: Write "সোম থেকে শুক্র, সকাল ৯ টা থেকে সন্ধ্যা ৭ টা পর্যন্ত।" For specific times: "বিকেল ৬ টা", "সন্ধ্যা ৭ টা", "দুপুর ২ টা ৩০ মিনিট"। (ALWAYS include spaces between number and 'টা').
  - Hindi: Write "सोमवार से शुक्रवार, सुबह 9 बजे से शाम 7 बजे तक।" For specific times: "शाम 6 बजे", "शाम 7 बजे", "दोपहर 2 बजकर 30 मिनट"।

## PRONUNCIATION & FORMAT RULES:
- NEVER write 'Dr.', 'Dr', 'ডা.', or 'ডাঃ'. ALWAYS write the full word: "Doctor" / "ডাক্তার" / "डॉक्टर".
- Maximum 1 to 2 short sentences per turn. Never monologue.
- Never info-dump phone numbers or addresses over voice.
- Script Integrity:
  - Bengali: 100% Bengali in Bangla script (বাংলা লিপি).
  - Hindi: Conversational Hindi with English loanwords in Latin script.
  - English: Conversational English.
- Closing: When caller says goodbye/thank you, speak a brief 1-sentence farewell and call `end_call` tool."""

    return prompt
