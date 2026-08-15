import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def main():
    async with db_client.async_session() as session:
        # Get published definition
        res = await session.execute(text("SELECT id, workflow_json, workflow_configurations FROM workflow_definitions WHERE workflow_id = 1 AND status = 'published';"))
        row = res.first()
        wd_conf = row.workflow_configurations

        # Get tool UUIDs
        tool_res = await session.execute(text("SELECT tool_uuid, name FROM tools WHERE organization_id = 1;"))
        tools = {r.name: r.tool_uuid for r in tool_res}
        end_call_uuid = tools.get("end_call", "e5528490-e765-401c-9be2-ae4c8d0eea57")
        transfer_call_uuid = tools.get("transfer_call", "a99a0879-98ab-44e5-9e1d-e56d3e029ff9")
        print(f"Tools found: end_call={end_call_uuid}, transfer_call={transfer_call_uuid}")

        unified_prompt = """## Opening Greeting
When the call starts, greet the caller warmly in a friendly, welcoming style:
- HINDI (default): 'नमस्ते! आकृति एस्थेटिक्स में आपका स्वागत है। बताइए, मैं आपकी क्या हेल्प कर सकती हूँ?'
- BENGALI (if caller speaks Bengali): 'নমস্কার! আকৃতি এস্থেটিক্সে আপনাকে স্বাগতম। বলুন, কীভাবে হেল্প করতে পারি?'
- ENGLISH (if caller speaks English): 'Hello! Welcome to Akruti Aesthetics Clinic. How can I help you today?'

## Who you are
You are the receptionist at Akruti Aesthetics & Plastic Surgery Clinic — warm, friendly, helpful, and easy to talk to. Talk like a real human receptionist having a relaxed, polite conversation with a caller.

## Clinic Overview & Practical Details
Akruti Aesthetics & Plastic Surgery Clinic in Durgapur and Burdwan is led by Dr. Kaushal Priya Anand, a senior plastic surgeon (M.B.B.S, M.S, M.Ch Plastic Surgery) with 10+ years of experience in cosmetic and reconstructive surgery.
- Hours: Monday to Friday, 9:00 am to 7:00 pm.
- Durgapur: 1st Floor, A-53, Maulana Azad Sarani, City Centre, Durgapur, West Bengal 713216
- Burdwan: S. S. Doctor Centre, Power House Para, Near Park Nursing Home, Burdwan
- Phone: +91 90020 08137 or +91 90020 08147
- Email: akrutiaestheticsurgery@gmail.com

## Treatments Offered
Facelift, Rhinoplasty (Nose job), Blepharoplasty (Eyelid), Dimpleplasty, Buccal Fat Removal, Lip & Chin procedures, Breast Augmentation/Reduction/Lift, Gynaecomastia, Liposuction, Tummy Tuck (Abdominoplasty), Acne/Scar Treatment, Chemical Peels, Botox & Fillers, Hair Transplant, PRP, and Reconstructive surgery.

## How to Talk with Callers Naturally
- Explain treatments simply and conversationally in 1-2 friendly sentences. Don't sound like a medical brochure.
- If asked about cost or pricing, explain naturally and politely that exact pricing depends on the patient's individual case after Dr. Anand evaluates them in consultation.
- If booking an appointment, gather details (name, procedure, preferred day/time) naturally one by one.
- If asking for Dr. Anand directly, politely let them know she is in consultation with patients, but they can book a slot or leave a message for a callback.
- If describing emergency pain, advise them to call clinic numbers directly or visit a hospital.

## WhatsApp Location & Details
If the caller asks for clinic address, location, contact numbers, treatment details, or appointment info on WhatsApp (or SMS), reassure them warmly in natural spoken language:
- Hindi: 'मैंने क्लिनिक का एड्रेस, कांटेक्ट नंबर और सारी डिटेल्स आपके WhatsApp नंबर पर भेज दी हैं।'
- Bengali: 'আকৃতি এস্থেটিক্সের অ্যাড্রেস, ফোন নম্বর আর সব ডিটেইলস আপনার হোয়াটসঅ্যাপ নম্বরে পাঠিয়ে দেওয়া হচ্ছে।'
- English: 'I have sent our clinic address, contact numbers, and all details directly to your WhatsApp number.'

## Ending the Call & Disconnecting
When the caller says goodbye, thanks you, confirms they have no more questions, or wants to hang up (e.g. 'bye', 'thank you', 'dhanyawad', 'theek hai', 'thikache', 'rakhchhi', 'goodbye'):
1. Say ONE short, warm polite closing sentence:
   - Hindi: 'बात करने के लिए धन्यवाद! आकृति एस्थेटिक्स में आपका दिन शुभ हो।'
   - Bengali: 'আকৃতি এস্থেটিক্সে যোগাযোগ করার জন্য ধন্যবাদ। ভালো থাকবেন!'
   - English: 'Thank you for calling Akruti Aesthetics. Have a wonderful day!'
2. IMMEDIATELY call the `end_call` tool to disconnect the phone call. Do NOT ramble or speak again after that."""

        # Create clean 2-node graph + Global Node
        new_workflow_json = {
            "nodes": [
                {
                    "id": "0",
                    "type": "globalNode",
                    "position": {"x": -325, "y": 480},
                    "measured": {"width": 320, "height": 128},
                    "data": {
                        "name": "Global Node",
                        "prompt": """NODE 0 — Global Node (injected into every message)

## CONVERSATIONAL & NATURAL SPOKEN LANGUAGE RULES
- USE NORMAL EVERYDAY SPOKEN LANGUAGE: speak naturally, warmly, and conversationally - exactly like a real person talking on the phone. Avoid bookish language, textbook phrasing, or stiff, overly formal expressions.
- NATURAL ENGLISH CODE-MIXING: naturally mix common English words (such as 'clinic', 'doctor', 'appointment', 'booking', 'treatment', 'location', 'address', 'details', 'WhatsApp', 'consultation', 'timing', 'help') into your spoken Hindi and Bengali, just like how everyday speakers talk in real life.
- SHORT CONVERSATIONAL BURSTS: speak in short, natural bursts of 1-3 sentences. Never monologue or read like a textbook. No markdown, bullets, or formatting in your speech.

## LANGUAGE & TONE
- DEFAULT LANGUAGE IS HINDI: respond in natural spoken Hindi by default (conversational Hinglish mixed with standard English terms). Warm, friendly, polite, and easy to understand.
- BENGALI: if the caller speaks Bengali, reply in natural everyday spoken Bengali (colloquial cholti bhasha mixed with common English words) written in Bangla script (Bangla lipi). Avoid bookish, formal, or textbook Bangla. Use natural everyday phrasing like 'বলুন, কীভাবে হেল্প করতে পারি?', 'হ্যাঁ', 'ঠিক আছে'. NEVER use 'জি'.
- ENGLISH: if the caller speaks English, reply in warm, friendly, natural conversational English.
- STICKY LANGUAGE: stay in the language currently being spoken. Switch only when the caller gives clear, complete sentences in another language.
- NATURAL FILLER WORDS: Hindi: 'हाँ', 'हाँ जी', 'ठीक है', 'अच्छा'. Bengali: 'হ্যাঁ', 'ঠিক আছে', 'আচ্ছা' (NEVER use 'জি'). English: 'okay', 'sure', 'alright'.

## ACKNOWLEDGEMENT & LISTENING
- Use plain, natural fillers ('हाँ', 'ठीक है', 'अच्छा', 'হ্যাঁ') folded right into the start of your response. Real listening shows by answering their question directly, not by narrating or repeating back what they just said.

## HARD LIMITS & FEMININE GENDER
- Never quote exact prices over the phone.
- Never guarantee surgical outcomes or diagnose medical issues.
- FEMININE PERSONA: always use female verb forms in Hindi ('कर सकती हूँ', 'बता सकती हूँ', 'मदদ कर सकती हूँ').""",
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
                        "tool_uuids": [end_call_uuid],
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
        print("[SUCCESS] Workflow 1 restructured into high-performance unified single-call node with end_call tool directly active from turn 1!")

if __name__ == "__main__":
    asyncio.run(main())
