import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def main():
    async with db_client.async_session() as session:
        # Get tool UUIDs
        tool_res = await session.execute(text("SELECT tool_uuid, name FROM tools WHERE organization_id = 1;"))
        tools = {r.name: r.tool_uuid for r in tool_res}
        end_call_uuid = tools.get("end_call", "e5528490-e765-401c-9be2-ae4c8d0eea57")
        transfer_call_uuid = tools.get("transfer_call", "a99a0879-98ab-44e5-9e1d-e56d3e029ff9")

        # Get published definition
        res = await session.execute(text("SELECT id FROM workflow_definitions WHERE workflow_id = 1 AND status = 'published';"))
        row = res.first()

        global_prompt = """## CORE SPOKEN & SCRIPT INTEGRITY RULES

1. STRICT SCRIPT ISOLATION:
   - BENGALI MODE: When the caller chooses Bengali or speaks Bengali, you MUST reply 100% in Bengali using Bangla script (বাংলা লিপি) only. NEVER mix Hindi/Devanagari letters or English Latin letters into Bengali responses, even if the caller's transcription appears in Devanagari or English.
   - HINDI MODE: When speaking Hindi, write English loanwords (clinic, address, doctor, appointment, WhatsApp, details, contact number) in standard English Latin alphabet.
   - ENGLISH MODE: Natural conversational English.

2. ZERO HALLUCINATION POLICY:
   - NEVER fabricate phone numbers (never use 9999999999), addresses, or doctors. Use ONLY the authentic clinic facts provided in your instructions.

3. CONVERSATIONAL STYLE:
   - This is a real voice call. Speak in 1 to 2 short, crisp, natural sentences.
   - NO MARKDOWN: Never output asterisks (**), bullet points (-), or markdown headers (#). Speak in clean plain text."""

        unified_prompt = """## Opening Action
When the call starts, greet the caller:
"नमस्ते! Welcome to Akruti Aesthetics & Plastic Surgery Clinic. Aap Hindi, Bengali, ya English — kis language me baat karna prefer karenge?"

## Language Handling
- If caller chooses BENGALI (or speaks Bengali):
  - Acknowledge in pure Bangla: "খুব ভালো! বলুন, আপনাকে কীভাবে সাহায্য করতে পারি?"
  - Lock into 100% pure Bengali in Bangla script (বাংলা লিপি) for the entire rest of the call.
- If caller chooses HINDI (or speaks Hindi):
  - Acknowledge in Hindi: "बहुत बढ़िया! बताइए, मैं आपकी क्या help कर सकती हूँ?"
  - Lock into conversational Hindi for the rest of the call.
- If caller chooses ENGLISH (or speaks English):
  - Acknowledge in English: "Great! How can I help you today?"
  - Lock into conversational English for the rest of the call.

## Who you are
You are the receptionist at Akruti Aesthetics & Plastic Surgery Clinic (আকৃতি এস্থেটিক্স অ্যান্ড প্লাস্টিক সার্জারি ক্লিনিক) — polite, friendly, and helpful.

## Authentic Clinic Details (Ground Truth)
- Clinic Name: Akruti Aesthetics & Plastic Surgery Clinic (আকৃতি এস্থেটিক্স অ্যান্ড প্লাস্টিক সার্জারি ক্লিনিক)
- Chief Surgeon: Dr. Kaushal Priya Anand (ডাক্তার কৌশল প্রিয়া আনন্দ), M.B.B.S, M.S, M.Ch Plastic Surgery, 10+ years experience.
- Clinic Timings: Monday to Friday, 9:00 am to 7:00 pm (সোম থেকে শুক্র, সকাল ৯টা থেকে সন্ধ্যা ৭টা).
- Authentic Phone: +91 90020 08137 / +91 90020 08147
- Authentic Email: akrutiaestheticsurgery@gmail.com
- Durgapur Address:
  - Bengali: ১ম তলা, এ-৫৩, মৌলানা আজাদ সরণি, সিটি সেন্টার, দুর্গাপুর, পশ্চিমবঙ্গ ৭১৩২১৬
  - Hindi: 1st Floor, A-53, Maulana Azad Sarani, City Centre, Durgapur, West Bengal 713216
  - English: 1st Floor, A-53, Maulana Azad Sarani, City Centre, Durgapur, West Bengal 713216
- Burdwan Address:
  - Bengali: এস. এস. ডাক্তার সেন্টার, পাওয়ার হাউস পাড়া, পার্ক নার্সিং হোমের কাছে, বর্ধমান
  - Hindi: S. S. Doctor Centre, Power House Para, Near Park Nursing Home, Burdwan
  - English: S. S. Doctor Centre, Power House Para, Near Park Nursing Home, Burdwan

## Treatments Offered
Facelift, Rhinoplasty, Blepharoplasty, Dimpleplasty, Buccal Fat Removal, Lip & Chin, Breast Surgery, Gynaecomastia, Liposuction, Tummy Tuck, Acne/Scar Treatment, Chemical Peels, Botox & Fillers, Hair Transplant, PRP, Reconstructive surgery.

## Conversational Guidelines
- Explain treatments in 1-2 friendly spoken sentences.
- Never quote exact prices over phone; pricing depends on evaluation during consultation with Dr. Anand.
- If booking an appointment, ask for their name, preferred date/time, and procedure.
- If sharing details on WhatsApp:
  - Bengali: "আমি আকৃতি এস্থেটিক্স অ্যান্ড প্লাস্টিক সার্জারি ক্লিনিকের সমস্ত ঠিকানা এবং ফোন নম্বর আপনার হোয়াটসঅ্যপ নম্বরে পাঠিয়ে দিচ্ছি।"
  - Hindi: "मैंने clinic का address, contact numbers और सारी details आपके WhatsApp number पर भेज दी हैं।"
  - English: "I have sent our clinic address, contact numbers, and details to your WhatsApp number."

## Natural Closing & Disconnection
When the caller is finished, says goodbye, or indicates they have no more questions ('thank you', 'bye', 'theek hai', 'thikache', 'rakhchhi', 'dhanyawad'):
1. Speak a natural, warm closing in the active language:
   - Bengali: "আকৃতি এস্থেটিক্স অ্যান্ড প্লাস্টিক সার্জারি ক্লিনিকে যোগাযোগ করার জন্য ধন্যবাদ। ভালো থাকবেন!"
   - Hindi: "Akruti Aesthetics & Plastic Surgery Clinic में call करने के लिए धन्यवाद! आपका दिन शुभ हो।"
   - English: "Thank you for calling Akruti Aesthetics & Plastic Surgery Clinic. Have a wonderful day!"
2. IMMEDIATELY call the `end_call` tool to disconnect the phone call."""

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
                        "name": "Akruti Receptionist",
                        "prompt": unified_prompt,
                        "is_start": True,
                        "delayed_start": False,
                        "allow_interrupt": True,
                        "add_global_prompt": True,
                        "tool_uuids": [end_call_uuid, transfer_call_uuid],
                        "extraction_enabled": True,
                        "extraction_prompt": "Extract caller details: preferred_language ('hindi', 'bengali', 'english'), caller_name, procedure_of_interest, booking_requested, preferred_date_time.",
                        "extraction_variables": [
                            {"name": "preferred_language", "type": "string", "description": "Preferred language: hindi, bengali, or english"},
                            {"name": "caller_name", "type": "string", "description": "Name of caller"},
                            {"name": "procedure_of_interest", "type": "string", "description": "Treatment asked about"},
                            {"name": "booking_requested", "type": "boolean", "description": "Whether an appointment was requested"},
                            {"name": "preferred_date_time", "type": "string", "description": "Preferred date or time"}
                        ]
                    }
                },
                {
                    "id": "2",
                    "type": "endCall",
                    "position": {"x": 175, "y": 500},
                    "measured": {"width": 320, "height": 128},
                    "data": {
                        "name": "End Call",
                        "is_end": True,
                        "prompt": "NODE 2 — End Call\n\nCall over. Do not speak.",
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
                        "condition": "Caller says goodbye, thank you, or indicates they want to hang up.",
                        "label": "End Call"
                    }
                }
            ],
            "start_node_id": "1"
        }

        # Update in database
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
        print("[SUCCESS] Published unified high-reliability workflow with full factual clinic context in all languages.")

if __name__ == "__main__":
    asyncio.run(main())
