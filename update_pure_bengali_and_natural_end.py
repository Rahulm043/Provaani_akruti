import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def main():
    async with db_client.async_session() as session:
        # 1. Reset end_call tool to messageType: 'none' so it does not play a hardcoded message
        tool_def = {
            "schema_version": 1,
            "type": "end_call",
            "config": {
                "messageType": "none",
                "customMessage": None,
                "audioRecordingId": None,
                "endCallReason": False,
                "endCallReasonDescription": None
            }
        }
        await session.execute(
            text("""
                UPDATE tools 
                SET definition = :definition,
                    updated_at = NOW()
                WHERE name = 'end_call' AND organization_id = 1;
            """),
            {"definition": json.dumps(tool_def)}
        )

        # 2. Get tool UUIDs
        tool_res = await session.execute(text("SELECT tool_uuid, name FROM tools WHERE organization_id = 1;"))
        tools = {r.name: r.tool_uuid for r in tool_res}
        end_call_uuid = tools.get("end_call", "e5528490-e765-401c-9be2-ae4c8d0eea57")
        transfer_call_uuid = tools.get("transfer_call", "a99a0879-98ab-44e5-9e1d-e56d3e029ff9")

        # 3. Get workflow definition
        res = await session.execute(text("SELECT id FROM workflow_definitions WHERE workflow_id = 1 AND status = 'published';"))
        row = res.first()

        global_prompt = """## LANGUAGE & SCRIPT RULES

1. PURE BENGALI SCRIPT RULE (CRITICAL):
   - When speaking in Bengali, generate EVERYTHING completely and exclusively in Bengali language using Bangla script (বাংলা লিপি).
   - DO NOT mix English Latin letters or any other language into Bengali responses.
   - Clinic name in Bengali: "আকৃতি এস্থেটিক্স অ্যান্ড প্লাস্টিক সার্জারি ক্লিনিক"
   - Locations in Bengali: "দুর্গাপুর" এবং "বর্ধমান"
   - Doctor name in Bengali: "ডাক্তার কৌশল প্রিয়া আনন্দ"
   - Every single word in Bengali mode must be written in proper Bangla script (বাংলা অক্ষর).

2. HINDI / HINGLISH SCRIPT RULE:
   - When speaking in Hindi, write English technical terms (clinic, address, WhatsApp, details, appointment, timing, contact number) in English Latin letters.
   - Example: "हाँ, ठीक है। हमारे clinic के दो address हैं: Durgapur और Burdwan।"

3. ENGLISH RULE:
   - When speaking in English, use natural conversational English.

4. NO MARKDOWN, NO BULLET POINTS, NO ASTERISKS:
   - Never output markdown lists, asterisks (**), bullets (-), or markdown headers. Speak in simple, clean conversational sentences.

5. SHORT NATURAL BURSTS:
   - Speak in 1 to 2 short, natural conversational sentences. Never monologue."""

        node1_prompt = """NODE 1 — Language Selection

## Opening Greeting
When the call connects, say:
"नमस्ते! Welcome to Akruti Aesthetics & Plastic Surgery Clinic. Aap Hindi, Bengali, ya English — kis language me baat karna prefer karenge?"

## Instructions
- If caller chooses Bengali (or speaks Bengali): reply warmly in pure Bangla script ("খুব ভালো! বলুন, আপনাকে কীভাবে সাহায্য করতে পারি?") and move to Main Consultation.
- If caller chooses Hindi: reply warmly in Hindi ("बहुत बढ़िया! बताइए, मैं आपकी क्या help कर सकती हूँ?") and move to Main Consultation.
- If caller chooses English: reply warmly in English ("Great! How can I help you today?") and move to Main Consultation.
- If the caller starts directly asking an inquiry in a specific language without naming one, match their language immediately and transition to Main Consultation."""

        node2_prompt = """NODE 2 — Main Clinic Consultation

## Language Adherence
- Continue strictly in the caller's chosen language.
- BENGALI: 100% pure Bengali in Bangla script (বাংলা লিপি). No English words or Latin letters mixed in.
- HINDI: Natural spoken Hindi with English words in English letters.
- ENGLISH: Natural conversational English.

## Who you are
You are the friendly, polite receptionist at Akruti Aesthetics & Plastic Surgery Clinic (আকৃতি এস্থেটিক্স অ্যান্ড প্লাস্টিক সার্জারি ক্লিনিক).

## Clinic Information & Doctor Details
- Led by Dr. Kaushal Priya Anand (ডাক্তার কৌশল প্রিয়া আনন্দ), senior plastic surgeon (M.B.B.S, M.S, M.Ch Plastic Surgery) with 10+ years experience.
- Hours: Monday to Friday, 9:00 am to 7:00 pm (সোম থেকে শুক্র, সকাল ৯টা থেকে সন্ধ্যা ৭টা).
- Durgapur: 1st Floor, A-53, Maulana Azad Sarani, City Centre, Durgapur (প্রথম তলা, এ-৫৩, মৌলানা আজাদ সরণি, সিটি সেন্টার, দুর্গাপুর)
- Burdwan: S. S. Doctor Centre, Power House Para, Near Park Nursing Home, Burdwan (এস. এস. ডাক্তার সেন্টার, পাওয়ার হাউস পাড়া, পার্ক নার্সিং হোমের কাছে, বর্ধমান)
- Phone: +91 90020 08137 / +91 90020 08147

## Treatments Offered
Facelift, Rhinoplasty, Blepharoplasty, Dimpleplasty, Buccal Fat Removal, Lip & Chin, Breast Surgery, Gynaecomastia, Liposuction, Tummy Tuck, Acne/Scar Treatment, Chemical Peels, Botox & Fillers, Hair Transplant, PRP, Reconstructive surgery.

## Conversational Guidelines
- Explain treatments in 1-2 friendly spoken sentences.
- Never quote exact prices over phone; pricing depends on evaluation during consultation with Dr. Anand.
- If booking an appointment, politely ask for their name, preferred date/time, and treatment of interest.
- If sharing details on WhatsApp:
  - Bengali: "আমি আকৃতি এস্থেটিক্স অ্যান্ড প্লাস্টিক সার্জারি ক্লিনিকের ঠিকানা, ফোন নম্বর এবং সমস্ত বিবরণ আপনার হোয়াটসঅ্যাপ নম্বরে পাঠিয়ে দিচ্ছি।"
  - Hindi: "मैंने clinic का address, contact numbers और सारी details आपके WhatsApp number पर भेज दी हैं।"
  - English: "I have sent our clinic address, contact numbers, and details to your WhatsApp number."

## Natural Farewell & Disconnection
When the caller is finished, thanks you, or wants to conclude the call:
1. Speak a natural, friendly closing response in the active language:
   - Bengali: "আকৃতি এস্থেটিক্স অ্যান্ড প্লাস্টিক সার্জারি ক্লিনিকে যোগাযোগ করার জন্য ধন্যবাদ। ভালো থাকবেন!"
   - Hindi: "Akruti Aesthetics & Plastic Surgery Clinic में call करने के लिए धन्यवाद! आपका दिन शुभ हो।"
   - English: "Thank you for calling Akruti Aesthetics & Plastic Surgery Clinic. Have a wonderful day!"
2. Call the `end_call` tool to disconnect the call."""

        new_workflow_json = {
            "nodes": [
                {
                    "id": "0",
                    "type": "globalNode",
                    "position": {"x": -325, "y": 480},
                    "measured": {"width": 320, "height": 128},
                    "data": {
                        "name": "Global Node",
                        "prompt": global_prompt,
                        "allow_interrupt": False
                    }
                },
                {
                    "id": "1",
                    "type": "startCall",
                    "position": {"x": 175, "y": 60},
                    "measured": {"width": 320, "height": 128},
                    "data": {
                        "name": "Language Selection",
                        "prompt": node1_prompt,
                        "is_start": True,
                        "delayed_start": False,
                        "allow_interrupt": True,
                        "add_global_prompt": True,
                        "tool_uuids": [],
                        "extraction_enabled": True,
                        "extraction_prompt": "Extract the caller's chosen language: preferred_language ('hindi', 'bengali', 'english').",
                        "extraction_variables": [
                            {"name": "preferred_language", "type": "string", "description": "Preferred language of caller: hindi, bengali, or english"}
                        ]
                    }
                },
                {
                    "id": "2",
                    "type": "agentNode",
                    "position": {"x": 615, "y": 250},
                    "measured": {"width": 320, "height": 128},
                    "data": {
                        "name": "Main Consultation",
                        "prompt": node2_prompt,
                        "allow_interrupt": True,
                        "add_global_prompt": True,
                        "tool_uuids": [end_call_uuid, transfer_call_uuid],
                        "extraction_enabled": True,
                        "extraction_prompt": "Extract caller details: caller_name, procedure_of_interest, booking_requested, preferred_date_time.",
                        "extraction_variables": [
                            {"name": "caller_name", "type": "string", "description": "Name of the caller"},
                            {"name": "procedure_of_interest", "type": "string", "description": "Cosmetic treatment asked about"},
                            {"name": "booking_requested", "type": "boolean", "description": "Whether an appointment was requested"},
                            {"name": "preferred_date_time", "type": "string", "description": "Preferred date or time"}
                        ]
                    }
                },
                {
                    "id": "3",
                    "type": "endCall",
                    "position": {"x": 175, "y": 600},
                    "measured": {"width": 320, "height": 128},
                    "data": {
                        "name": "End Call",
                        "is_end": True,
                        "prompt": "NODE 3 — End Call\n\nCall over. Do not speak.",
                        "allow_interrupt": False,
                        "add_global_prompt": False,
                        "extraction_enabled": False,
                        "extraction_prompt": "",
                        "extraction_variables": [],
                        "tool_uuids": []
                    }
                }
            ],
            "edges": [
                {
                    "id": "1-2",
                    "source": "1",
                    "target": "2",
                    "type": "custom",
                    "animated": True,
                    "data": {
                        "condition": "Caller selects their preferred language or asks a question.",
                        "label": "Language Selected"
                    }
                },
                {
                    "id": "2-3",
                    "source": "2",
                    "target": "3",
                    "type": "custom",
                    "animated": True,
                    "data": {
                        "condition": "Caller says goodbye, thank you, or indicates they want to hang up.",
                        "label": "End Call"
                    }
                }
            ],
            "start_node_id": "1"
        }

        # Save to database
        await session.execute(
            text("""
                UPDATE workflow_definitions 
                SET workflow_json = :wf_json,
                    status = 'published'
                WHERE id = :id;
            """),
            {"wf_json": json.dumps(new_workflow_json), "id": row.id}
        )

        await session.commit()
        print("[SUCCESS] Updated workflow with pure Bengali script rules and natural conversational farewell.")

if __name__ == "__main__":
    asyncio.run(main())
