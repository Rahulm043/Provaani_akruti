import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def main():
    async with db_client.async_session() as session:
        # Get published definition ID
        res = await session.execute(text("SELECT id, workflow_configurations FROM workflow_definitions WHERE workflow_id = 1 AND status = 'published';"))
        row = res.first()

        # Get tool UUIDs
        tool_res = await session.execute(text("SELECT tool_uuid, name FROM tools WHERE organization_id = 1;"))
        tools = {r.name: r.tool_uuid for r in tool_res}
        end_call_uuid = tools.get("end_call", "e5528490-e765-401c-9be2-ae4c8d0eea57")
        transfer_call_uuid = tools.get("transfer_call", "a99a0879-98ab-44e5-9e1d-e56d3e029ff9")

        global_prompt = """## CRITICAL SPOKEN SCRIPT RULES (FOR TTS PRONUNCIATION)
1. CLINIC NAME:
   - The full official name is: "Akruti Aesthetics & Plastic Surgery Clinic"
   - Always use this full name when greeting or saying goodbye.

2. ALWAYS WRITE ALL ENGLISH WORDS IN STANDARD ENGLISH SCRIPT (LATIN LETTERS):
   - Whenever you speak an English word (e.g., clinic, doctor, appointment, booking, treatment, location, address, details, WhatsApp, consultation, timing, phone number, help, surgery, language), you MUST write it in standard English Latin alphabet.
   - NEVER transliterate English words into Devanagari or Bengali script (NEVER write 'एड्रेस', 'क्लिनिक', 'व्हाट्सएप', 'फोन नंबर', 'डिटेल', 'ক্লিনিক', 'অ্যাড্রেস', 'হোয়াটসঅ্যাপ').
   - Correct Hindi: "हाँ, ठीक है। हमारे clinic के दो address हैं: Durgapur और Burdwan। मैं सारी details आपके WhatsApp number पर भेज देती हूँ।"
   - Correct Bengali: "হ্যাঁ, ঠিক আছে। আমাদের clinic এর দুটো address আছে: Durgapur আর Burdwan। আমি সব details আপনার WhatsApp number এ পাঠিয়ে দিচ্ছি।"

3. NO MARKDOWN, NO BULLET POINTS, NO ASTERISKS:
   - This is a voice phone call. Never generate markdown lists, asterisks (**), bullets (-), or headers (#). Speak only in clean plain sentences.

4. SHORT CONVERSATIONAL BURSTS:
   - Speak in 1 to 2 short, crisp sentences. Never monologue or read long paragraphs."""

        node1_prompt = """NODE 1 — Language Selection

## Opening Greeting
Your first action when the call starts is to say:
"नमस्ते! Welcome to Akruti Aesthetics & Plastic Surgery Clinic. Aap Hindi, Bengali, ya English — kis language me baat karna prefer karenge?"

## Instruction
- Listen to the caller's language preference (Hindi, Bengali/Bangla, or English).
- If caller chooses Hindi: acknowledge warmly in Hindi ("बहुत बढ़िया! बताइए, मैं आपकी क्या help कर सकती हूँ?") and transition to Main Consultation.
- If caller chooses Bengali: acknowledge warmly in Bengali ("খুব ভালো! বলুন, কীভাবে help করতে পারি?") and transition to Main Consultation.
- If caller chooses English: acknowledge warmly in English ("Great! How can I help you today?") and transition to Main Consultation.
- If the caller directly asks a question without explicitly naming a language, acknowledge their question in the language they spoke and transition to Main Consultation immediately."""

        node2_prompt = """NODE 2 — Main Clinic Consultation

## Language Adherence
- Continue strictly in the language chosen or spoken by the caller in Node 1 (Hindi, Bengali, or English).
- Write all English terms in Latin alphabet (e.g., clinic, address, doctor, appointment, WhatsApp, details).

## Who you are
You are the receptionist at Akruti Aesthetics & Plastic Surgery Clinic — warm, polite, and helpful.

## Clinic Overview & Details
Akruti Aesthetics & Plastic Surgery Clinic is led by Dr. Kaushal Priya Anand (M.B.B.S, M.S, M.Ch Plastic Surgery) with 10+ years experience.
- Hours: Monday to Friday, 9:00 am to 7:00 pm.
- Durgapur address: 1st Floor, A-53, Maulana Azad Sarani, City Centre, Durgapur
- Burdwan address: S. S. Doctor Centre, Power House Para, Near Park Nursing Home, Burdwan
- Phone: +91 90020 08137 / +91 90020 08147
- Email: akrutiaestheticsurgery@gmail.com

## Treatments Offered
Facelift, Rhinoplasty, Blepharoplasty, Dimpleplasty, Buccal Fat Removal, Lip & Chin, Breast Augmentation/Reduction, Gynaecomastia, Liposuction, Tummy Tuck, Acne/Scar Treatment, Chemical Peels, Botox & Fillers, Hair Transplant, PRP, and Reconstructive surgery.

## Guidelines
- Explain treatments in 1-2 friendly spoken sentences.
- Never quote exact prices over phone; pricing depends on consultation evaluation by Dr. Anand.
- If booking an appointment, ask for their name, preferred day/time, and procedure.
- If asking for details on WhatsApp:
  - Hindi: 'मैंने clinic का address, contact numbers और सारी details आपके WhatsApp number पर भेज दी हैं।'
  - Bengali: 'Akruti Aesthetics & Plastic Surgery Clinic এর address, phone number আর সব details আপনার WhatsApp number এ পাঠিয়ে দেওয়া হচ্ছে।'
  - English: 'I have sent our clinic address, contact numbers, and all details directly to your WhatsApp number.'

## Ending the Call & Disconnection
Whenever the caller indicates they are done or says goodbye ('thank you', 'bye', 'theek hai', 'thikache', 'rakhchhi', 'nahi theek hai'):
1. Speak the warm closing salutation:
   - Hindi: 'Akruti Aesthetics & Plastic Surgery Clinic में call करने के लिए धन्यवाद! आपका दिन शुभ हो।'
   - Bengali: 'Akruti Aesthetics & Plastic Surgery Clinic এ যোগাযোগ করার জন্য ধন্যবাদ। ভালো থাকবেন!'
   - English: 'Thank you for calling Akruti Aesthetics & Plastic Surgery Clinic. Have a wonderful day!'
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
                        "condition": "Caller selects their preferred language (Hindi, Bengali, English) or asks a question.",
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
        print("[SUCCESS] Language Selection workflow (Hindi, Bengali, English) published to PostgreSQL.")

if __name__ == "__main__":
    asyncio.run(main())
