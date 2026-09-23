import os
import json
import asyncio
from api.db import db_client
from sqlalchemy import text

CEREBRAS_KEY = os.environ.get("CEREBRAS_API_KEY", "")
SMALLEST_KEY = os.environ.get("SMALLEST_API_KEY", "")

async def main():
    async with db_client.async_session() as session:
        # Get tool UUIDs
        tool_res = await session.execute(text("SELECT tool_uuid, name FROM tools WHERE organization_id = 1;"))
        tools = {r.name: r.tool_uuid for r in tool_res}
        end_call_uuid = tools.get("end_call", "e5528490-e765-401c-9be2-ae4c8d0eea57")
        transfer_call_uuid = tools.get("transfer_call", "a99a0879-98ab-44e5-9e1d-e56d3e029ff9")
        send_whatsapp_uuid = tools.get("send_whatsapp", "b72e905a-5942-4f9e-a228-48b0c411c521")

        # Get published definition
        res = await session.execute(text("SELECT id FROM workflow_definitions WHERE workflow_id = 1 AND status = 'published';"))
        row = res.first()

        # Update workflow configurations (LLM temp=0.1, TTS speed=0.9)
        workflow_configurations = {
            "model_configuration_v2_override": {
                "byok": {
                    "mode": "pipeline",
                    "pipeline": {
                        "llm": {
                            "provider": "openai",
                            "model": "gpt-oss-120b",
                            "base_url": "https://api.cerebras.ai/v1",
                            "api_key": [CEREBRAS_KEY],
                            "temperature": 0.1
                        },
                        "stt": {
                            "provider": "smallest",
                            "model": "pulse",
                            "language": "north_indic",
                            "api_key": [SMALLEST_KEY],
                            "keywords": "blepharoplasty, rhinoplasty, dimpleplasty, buccal fat, gynaecomastia, liposuction, abdominoplasty, tummy tuck, cryolipolysis, micropigmentation, akruti, anand, durgapur, burdwan, whatsapp"
                        },
                        "tts": {
                            "provider": "smallest",
                            "model": "lightning_v3.1_pro",
                            "voice": "meher",
                            "language": "auto",
                            "speed": 0.9,
                            "api_key": [SMALLEST_KEY]
                        }
                    }
                },
                "mode": "byok",
                "version": 2
            },
            "dictionary": "blepharoplasty, rhinoplasty, dimpleplasty, buccal fat, gynaecomastia, liposuction, abdominoplasty, tummy tuck, cryolipolysis, micropigmentation, aakruti, akruti, anand, durgapur, burdwan, whatsapp",
            "max_call_duration": 600,
            "max_user_idle_timeout": 30,
            "user_turn_stop_timeout": 0.8
        }

        unified_prompt = """## OPENING GREETING (Say this exact phrase on call start):
"नमस्ते! Welcome to Aakruti Aesthetics & Plastic Surgery Clinic. ... Aap kis language me baat karna prefer karenge? ... Hindi, Bengali, ya English?"

## LANGUAGE HANDLING:
- If caller chooses BENGALI (or speaks Bengali): Reply warmly in pure Bangla ("খুব ভালো! বলুন, আপনাকে কীভাবে সাহায্য করতে পারি?") and lock strictly into 100% Bengali in Bangla script (বাংলা লিপি) for the entire call.
- If caller chooses HINDI (or speaks Hindi): Reply warmly in Hindi ("बहुत बढ़िया! बताइए, मैं आपकी क्या help कर सकती हूँ?") and lock into conversational Hindi.
- If caller chooses ENGLISH (or speaks English): Reply warmly in English ("Great! How can I help you today?") and lock into English.

## AUTHENTIC CLINIC FACTS (GROUND TRUTH ONLY — NEVER INVENT ANY DETAILS):
- Clinic Name: Aakruti Aesthetics & Plastic Surgery Clinic (আকৃতি এস্থেটিক্স অ্যান্ড প্লাস্টিক সার্জারি ক্লিনিক)
- Chief Surgeon: Doctor Kaushal Priya Anand (বাংলায়: ডাক্তার কৌশল প্রিয়া আনন্দ, हिंदी: डॉक्टर कौशल प्रिया आनंद), M.B.B.S, M.S, M.Ch Plastic Surgery, 20+ years of excellence.
- Hours: Monday to Friday, 9:00 am to 7:00 pm (সোম থেকে শুক্র, সকাল ৯টা থেকে সন্ধ্যা ৭টা). Closed on weekends.
- Official Reception & Appointment Numbers: +91 90020 08137 / +91 90020 08147 (ফোন: +৯১ ৯০০২০ ০৮১৩৭ / +৯১ ৯০০২০ ০৮১৪৭)
- Official Email: akrutiaestheticsurgery@gmail.com
- Durgapur Address: First Floor, A-53, Maulana Azad Sarani, City Centre, Durgapur, West Bengal 713216 (১ম তলা, এ-৫৩, মৌলানা আজাদ সরণি, সিটি সেন্টার, দুর্গাপুর)
- Burdwan Address: S. S. Doctor Centre, Power House Para, Near Park Nursing Home, Burdwan (এস. এস. ডাক্তার সেন্টার, পাওয়ার হাউস পাড়া, পার্ক নার্সিং হোমের কাছে, বর্ধমান)

## PROCEDURES OFFERED:
- Head & Face: Facelift, Asian Eyelid Blepharoplasty, Dimpleplasty, Buccal Fat Pad Removal, Rhinoplasty, Lip Augmentation & Reduction, Chin Augmentation, Ear Reconstruction.
- Breast Surgery: Breast Augmentation, Breast Reduction, Breast Lift, Gynaecomastia Surgery.
- Tummy & Body Contouring: Liposuction, Tummy Tuck (Abdominoplasty), Mini Tummy Tuck, 6-pack Abs, Arm Lift, Thigh Lift, Fat Grafting, Buttock Contouring.
- Skin Treatments: Acne & Acne Scars, Chemical Peels, Micro Needling, Mole Excision, Botox & Fillers, Medical Facial, Cryolipolysis.
- Hair Treatments: Hair Transplant, PRP (Platelet-Rich Plasma), Eyebrow Transplant, Beard & Moustache Transplant, Scalp & Eyebrow Micropigmentation.
- Reconstructive & Trauma: Burns & Burn Deformities, Maxillofacial Surgery, Trauma & Replantation.

## NATURAL CONVERSATIONAL STYLE & PROCEDURE INQUIRIES (NO TEXTBOOK DEFINITIONS):
- When a caller mentions a procedure (e.g. Liposuction, Rhinoplasty, Hair Transplant, Gynecomastia, Blepharoplasty):
  - Do NOT give a textbook medical definition or clinical lecture.
  - Instead, respond warmly and conversationally as an experienced clinic assistant. Acknowledge that Doctor Kaushal Priya Anand performs this procedure regularly at Aakruti Aesthetics, and ask a relevant, consultative follow-up question.
  - Examples:
    - Bengali (Liposuction): "হ্যাঁ, আকৃতি ক্লিনিকে ডাক্তার কৌশল প্রিয়া আনন্দ নিয়মিত Liposuction সার্জারি করেন। আপনি কি শরীরের নির্দিষ্ট কোনো অংশের জন্য এটি বিবেচনা করছেন?"
    - Hindi (Liposuction): "हाँ, Aakruti Clinic में Doctor Kaushal Priya Anand regular basis पर Liposuction perform करते हैं। क्या आप body के किसी specific area के लिए सोच रहे हैं?"
    - English (Liposuction): "Yes, Doctor Kaushal Priya Anand routinely performs Liposuction at Aakruti Clinic. Are you looking for contouring in a specific area like the abdomen or flanks?"
    - Bengali (Rhinoplasty): "হ্যাঁ, ডাক্তার আনন্দ নাকের গঠন সুন্দর করার জন্য নিয়মিত Rhinoplasty করে থাকেন। আপনি কি কসমেটিক নাকি শ্বাস-প্রশ্বাসের সুবিধার জন্য ভাবছেন?"
  - ONLY define the procedure if the caller explicitly asks "What does this procedure mean?" or "How is it done?".

## WHATSAPP OFFERING TIMING & KEYPAD (DTMF) COLLECTION FLOW:
- TIMING (CRITICAL):
  - DO NOT offer WhatsApp at the get-go, opening, or during initial procedure queries.
  - Offer WhatsApp ONLY when:
    1. The caller explicitly asks for clinic address, timings, doctor details, booking, or contact numbers, OR
    2. Later in the call after discussing the procedure, when the caller shows clear interest in consulting Doctor Anand or visiting the clinic.
- KEYPAD (DTMF) NUMBER COLLECTION FLOW:
  1. Ask Caller to Type on Keypad (NEVER ask them to speak their number):
     - Bengali: "দয়া করে আপনার ফোনের keypad-এ আপনার ১০ ডিজিটের হোয়াটসঅ্যাপ নম্বরটি টাইপ করুন, আমি আকৃতি ক্লিনিক ও ডাক্তার আনন্দের সমস্ত বিবরণ পাঠিয়ে দিচ্ছি।"
     - Hindi: "कृपया अपने फोन के keypad पर अपना 10 अंकों का WhatsApp नंबर टाइप करें, मैं Aakruti Clinic और Doctor Anand की सारी डिटेल्स भेज देती हूँ।"
     - English: "Please type your 10-digit WhatsApp number on your phone keypad, and I will send the clinic details and reception numbers to you."
  2. When 10 Digits Arrive via Keypad (Received as `[Keypad Input Received: <10-digit number>]`):
     - Acknowledge naturally in 1 short sentence with the received number and confirm WhatsApp dispatch:
       - Bengali: "ঠিক আছে, আমি [Number] নম্বরে আকৃতি ক্লিনিক ও ডাক্তার আনন্দের সমস্ত বিবরণ হোয়াটসঅ্যাপে পাঠিয়ে দিচ্ছি। আপনি রিসেপশনে ফোন করে সরাসরি অ্যাপয়েন্টমেন্ট বুক করতে পারেন।"
       - Hindi: "ठीक है, मैं [Number] पर Aakruti Clinic और Doctor Anand की सारी डिटेल्स WhatsApp कर रही हूँ। आप रिसेप्शन पर कॉल करके अपॉइंटमेंट बुक कर सकते हैं।"
       - English: "Okay, I'm sending the clinic details and Doctor Anand's consultation info to [Number] on WhatsApp right now. You can call our reception directly to book your appointment."
     - IMMEDIATELY call `send_whatsapp` tool with `phone_number` and `procedure_of_interest`.
  3. If Caller Speaks Their Number Instead of Typing:
     - Politely prompt them to use their keypad:
       - Bengali: "দয়া করে নম্বরটি মুখে না বলে আপনার ফোনের keypad-এ টাইপ করুন।"
       - Hindi: "कृपया नंबर बोलकर नहीं, अपने फोन के keypad पर टाइप करें।"
       - English: "Please type the 10-digit number on your keypad instead of speaking it."

## NO DIRECT APPOINTMENT BOOKING:
- Appointments are scheduled directly by our reception team. Never say "Your appointment is booked".

## PRONUNCIATION & FORMAT RULES:
- NEVER write 'Dr.', 'Dr', 'ডা.', or 'ডাঃ'. ALWAYS write the full word: "Doctor" / "ডাক্তার" / "डॉक्टर".
- Maximum 1 to 2 short sentences per turn. Never monologue.
- Never info-dump phone numbers or addresses over voice. Offer WhatsApp instead when requested.
- Script Integrity:
  - Bengali: 100% Bengali in Bangla script (বাংলা লিপি).
  - Hindi: Conversational Hindi with English loanwords in Latin script.
  - English: Conversational English.
- Closing: When caller says goodbye/thank you, speak a brief 1-sentence farewell and call `end_call` tool."""

        new_workflow_json = {
            "nodes": [
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
                        "add_global_prompt": False,
                        "tool_uuids": [end_call_uuid, transfer_call_uuid, send_whatsapp_uuid],
                        "extraction_enabled": True,
                        "extraction_prompt": "Extract caller details: preferred_language, caller_name, procedure_of_interest, whatsapp_number, whatsapp_confirmed.",
                        "extraction_variables": [
                            {"name": "preferred_language", "type": "string", "description": "Preferred language: hindi, bengali, or english"},
                            {"name": "caller_name", "type": "string", "description": "Name of caller"},
                            {"name": "procedure_of_interest", "type": "string", "description": "Procedure asked about"},
                            {"name": "whatsapp_number", "type": "string", "description": "WhatsApp phone number provided or confirmed by caller"},
                            {"name": "whatsapp_confirmed", "type": "boolean", "description": "Whether WhatsApp dispatch was confirmed"}
                        ]
                    }
                }
            ],
            "edges": []
        }

        if row:
            def_id = row.id
            await session.execute(
                text("""
                    UPDATE workflow_definitions 
                    SET workflow_configurations = :config,
                        workflow_json = :data,
                        status = 'published'
                    WHERE id = :id;
                """),
                {
                    "config": json.dumps(workflow_configurations),
                    "data": json.dumps(new_workflow_json),
                    "id": def_id
                }
            )
            await session.execute(
                text("""
                    UPDATE workflows 
                    SET workflow_configurations = :config
                    WHERE id = 1;
                """),
                {
                    "config": json.dumps(workflow_configurations)
                }
            )
            print(f"[SUCCESS] Updated published definition ID {def_id}.")
        else:
            print("[ERROR] No published workflow definition found for workflow_id = 1.")

        await session.commit()

if __name__ == "__main__":
    asyncio.run(main())
