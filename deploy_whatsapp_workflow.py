import asyncio
import json
import uuid
import os
import sys

from api.db import db_client
from sqlalchemy import text

CEREBRAS_KEY = os.environ.get("CEREBRAS_API_KEY", "")
SMALLEST_KEY = os.environ.get("SMALLEST_API_KEY", "")

WHATSAPP_TOOL_UUID = "b72e905a-5942-4f9e-a228-48b0c411c521"

async def main():
    async with db_client.async_session() as session:
        print("=== 1. Ensuring send_whatsapp tool exists in database ===")
        res = await session.execute(text("SELECT id, tool_uuid, name FROM tools WHERE name = 'send_whatsapp' AND organization_id = 1;"))
        existing_tool = res.first()

        tool_def = {
            "schema_version": 1,
            "type": "http_api",
            "config": {
                "method": "POST",
                "url": "http://dograhtest-analysis:8001/send-whatsapp",
                "headers": {
                    "Content-Type": "application/json"
                },
                "parameters": [
                    {
                        "name": "phone_number",
                        "type": "string",
                        "description": "The caller's 10-digit WhatsApp phone number entered via DTMF keypad.",
                        "required": True
                    },
                    {
                        "name": "caller_name",
                        "type": "string",
                        "description": "The full name of the patient/caller.",
                        "required": False
                    },
                    {
                        "name": "procedure_of_interest",
                        "type": "string",
                        "description": "The aesthetic or plastic surgery procedure enquired about.",
                        "required": False
                    },
                    {
                        "name": "appointment_datetime",
                        "type": "string",
                        "description": "Requested or confirmed appointment date & time (e.g. 'Monday, 22 Sep at 3:30 PM').",
                        "required": False
                    },
                    {
                        "name": "branch",
                        "type": "string",
                        "description": "Clinic branch: 'durgapur' or 'burdwan'.",
                        "required": False
                    },
                    {
                        "name": "template_type",
                        "type": "string",
                        "description": "'clinic_details', 'appointment_confirmation', or 'appointment_details'.",
                        "required": False
                    }
                ],
                "body_template": {
                    "phone_number": "{{ phone_number }}",
                    "caller_name": "{{ caller_name }}",
                    "procedure_of_interest": "{{ procedure_of_interest }}",
                    "appointment_datetime": "{{ appointment_datetime }}",
                    "branch": "{{ branch }}",
                    "template_type": "{{ template_type }}"
                },
                "timeout_ms": 10000
            }
        }

        if existing_tool:
            whatsapp_uuid = existing_tool.tool_uuid
            await session.execute(
                text("UPDATE tools SET definition = :def, description = :desc WHERE id = :id;"),
                {
                    "def": json.dumps(tool_def),
                    "desc": "Send Akruti Aesthetics clinic details or confirmed appointment details to caller via WhatsApp.",
                    "id": existing_tool.id
                }
            )
            print(f"Updated existing send_whatsapp tool (UUID: {whatsapp_uuid}).")
        else:
            whatsapp_uuid = WHATSAPP_TOOL_UUID
            await session.execute(
                text("""
                    INSERT INTO tools (tool_uuid, organization_id, name, description, category, status, definition, created_by, created_at, updated_at)
                    VALUES (:uuid, 1, 'send_whatsapp', 'Send Akruti Aesthetics clinic details or confirmed appointment details to caller via WhatsApp.', 'http_api', 'active', :def, 1, NOW(), NOW());
                """),
                {
                    "uuid": whatsapp_uuid,
                    "def": json.dumps(tool_def)
                }
            )
            print(f"Created new send_whatsapp tool (UUID: {whatsapp_uuid}).")

        # Get other tool UUIDs
        tool_res = await session.execute(text("SELECT tool_uuid, name FROM tools WHERE organization_id = 1;"))
        tools = {r.name: r.tool_uuid for r in tool_res}
        end_call_uuid = tools.get("end_call", "e5528490-e765-401c-9be2-ae4c8d0eea57")
        transfer_call_uuid = tools.get("transfer_call", "a99a0879-98ab-44e5-9e1d-e56d3e029ff9")
        send_whatsapp_uuid = tools.get("send_whatsapp", whatsapp_uuid)

        print(f"Active Tool UUIDs: end_call={end_call_uuid}, send_whatsapp={send_whatsapp_uuid}")

        # Update workflow configurations
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
            "dictionary": "blepharoplasty, rhinoplasty, dimpleplasty, buccal fat, gynaecomastia, liposuction, abdominoplasty, tummy tuck, cryolipolysis, micropigmentation, akruti, anand, durgapur, burdwan, whatsapp",
            "max_call_duration": 600,
            "max_user_idle_timeout": 30,
            "user_turn_stop_timeout": 0.8
        }

        unified_prompt = """## OPENING GREETING (Say this exact phrase on call start):
"नमस्ते! Welcome to Akruti Aesthetics & Plastic Surgery Clinic. ... Aap kis language me baat karna prefer karenge? ... Hindi, Bengali, ya English?"

## LANGUAGE HANDLING:
- If caller chooses BENGALI (or speaks Bengali): Reply warmly in pure Bangla ("খুব ভালো! বলুন, আপনাকে কীভাবে সাহায্য করতে পারি?") and lock strictly into 100% Bengali in Bangla script (বাংলা লিপি) for the entire call.
- If caller chooses HINDI (or speaks Hindi): Reply warmly in Hindi ("बहुत बढ़िया! बताइए, मैं आपकी क्या help कर सकती हूँ?") and lock into conversational Hindi.
- If caller chooses ENGLISH (or speaks English): Reply warmly in English ("Great! How can I help you today?") and lock into English.

## AUTHENTIC CLINIC FACTS (GROUND TRUTH ONLY — NEVER INVENT ANY DETAILS):
- Clinic Name: Akruti Aesthetics & Plastic Surgery Clinic (আকৃতি এস্থেটিক্স অ্যান্ড প্লাস্টিক সার্জারি ক্লিনিক)
- Chief Surgeon: Doctor Kaushal Priya Anand (বাংলায়: ডাক্তার কৌশল প্রিয়া আনন্দ, हिंदी: डॉक्टर कौशल प्रिया आनंद), M.B.B.S, M.S, M.Ch Plastic Surgery, 20+ years of excellence.
- Hours: Monday to Friday, 9 AM to 7 PM (সোম থেকে শুক্র, সকাল ৯ টা থেকে সন্ধ্যা ৭ টা পর্যন্ত). Closed on weekends.
- Official Reception & Appointment Numbers: +91 90020 08137 / +91 90020 08147
- Official Email: akrutiaestheticsurgery@gmail.com
- Durgapur Address: First Floor, A-53, Maulana Azad Sarani, City Centre, Durgapur, West Bengal 713216 (১ম তলা, এ-৫৩, মৌলানা আজাদ সরণি, সিটি সেন্টার, দুর্গাপুর)
- Burdwan Address: S. S. Doctor Centre, Power House Para, Near Park Nursing Home, Burdwan (এস. এস. ডাক্তার সেন্টার, পাওয়ার হাউস পাড়া, পার্ক নার্সিং হোমের কাছে, বর্ধমান)

## STRICT TIME & NUMBER PRONUNCIATION (CRITICAL FOR NATURAL SPEECH):
- NEVER write times with colons and double zeroes (NEVER write '9:00', '6:00', '7:00', '09:00', '19:00').
- NEVER rush or concatenate numbers. ALWAYS insert punctuation (commas, periods) and spaces for natural breathing pauses.
- Exact language rules:
  - In English: Write "9 AM to 7 PM", "6 PM", "7 PM", "2:30 PM". Always say e.g. "Monday to Friday, 9 AM to 7 PM."
  - In Bengali: Write "সোম থেকে শুক্র, সকাল ৯ টা থেকে সন্ধ্যা ৭ টা পর্যন্ত।" For specific times: "বিকেল ৬ টা", "সন্ধ্যা ৭ টা", "দুপুর ২ টা ৩০ মিনিট"। (ALWAYS include spaces between number and 'টা').
  - In Hindi: Write "सोमवार से शुक्रवार, सुबह 9 बजे से शाम 7 बजे तक।" For specific times: "शाम 6 बजे", "शाम 7 बजे", "दोपहर 2 बजकर 30 मिनट"।

## PROCEDURES OFFERED:
- Head & Face: Facelift, Asian Eyelid Blepharoplasty, Dimpleplasty, Buccal Fat Pad Removal, Rhinoplasty, Lip Augmentation & Reduction, Chin Augmentation, Ear Reconstruction.
- Breast Surgery: Breast Augmentation, Breast Reduction, Breast Lift, Gynaecomastia Surgery.
- Tummy & Body Contouring: Liposuction, Tummy Tuck (Abdominoplasty), Mini Tummy Tuck, 6-pack Abs, Arm Lift, Thigh Lift, Fat Grafting, Buttock Contouring.
- Skin Treatments: Acne & Acne Scars, Chemical Peels, Micro Needling, Mole Excision, Botox & Fillers, Medical Facial, Cryolipolysis.
- Hair Treatments: Hair Transplant, PRP (Platelet-Rich Plasma), Eyebrow Transplant, Beard & Moustache Transplant, Scalp & Eyebrow Micropigmentation.
- Reconstructive & Trauma: Burns & Burn Deformities, Maxillofacial Surgery, Trauma & Replantation.

## PHONETIC MISHEARING & ALIAS MAPPING:
- "black board" / "black plastic" / "blefaro" / "eyelid" -> Blepharoplasty (Asian Eyelid Surgery)
- "rino" / "reno" / "nose plastic" / "nose job" -> Rhinoplasty
- "dimple" / "dimple plastic" -> Dimpleplasty
- "black fat" / "bukal" / "cheek fat" -> Buccal Fat Pad Removal
- "gaino" / "gyno" / "male chest" -> Gynaecomastia
- "tomi" / "tummy" / "abdomino" -> Tummy Tuck (Abdominoplasty)
- "lipo" / "lepo" / "fat suction" -> Liposuction

## WHATSAPP DISPATCH & DTMF KEYPAD COLLECTION RULES:
1. WHATSAPP NUMBER COLLECTION VIA DTMF KEYPAD ONLY:
   - When caller asks for details, clinic addresses, or appointment timings on WhatsApp:
   - NEVER ask caller to speak the number aloud. ALWAYS ask them to type the 10 digits on their phone dialpad:
     - Bengali: "দয়া করে আপনার ফোনের ডায়ালপ্যাডে ১০ সংখ্যার হোয়াটসঅ্যাপ নম্বরটি টাইপ করুন।"
     - Hindi: "कृपया अपने फ़ोन के डायलपैड पर 10 अंकों का WhatsApp नंबर टाइप करें।"
     - English: "Please enter your 10-digit WhatsApp number on your phone keypad."
2. CONFIRM AND DISPATCH:
   - When DTMF digits are received:
     - Bengali: "আপনার নম্বরটি কি [Number]?"
     - Hindi: "क्या आपका नंबर [Number] है?"
     - English: "Just to confirm, is your number [Number]?"
   - Once confirmed, IMMEDIATELY call `send_whatsapp` with `phone_number`.
3. HARD 2-SENTENCE LIMIT: Always respond in MAXIMUM 1 to 2 short, crisp sentences.
4. CLOSING & DISCONNECT: When the conversation concludes, speak a brief 1-sentence farewell and call `end_call`."""

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
                            {"name": "whatsapp_confirmed", "type": "boolean", "description": "Whether caller confirmed receiving WhatsApp details"}
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
        res = await session.execute(text("SELECT id FROM workflow_definitions WHERE workflow_id = 1 AND status = 'published';"))
        def_row = res.first()
        def_id = def_row.id if def_row else 1

        await session.execute(
            text("""
                UPDATE workflow_definitions 
                SET workflow_json = :wf_json,
                    workflow_configurations = :wf_config,
                    status = 'published'
                WHERE id = :id;
            """),
            {
                "wf_json": json.dumps(new_workflow_json),
                "wf_config": json.dumps(workflow_configurations),
                "id": def_id
            }
        )

        await session.execute(
            text("""
                UPDATE workflows 
                SET workflow_configurations = :wf_config
                WHERE id = 1;
            """),
            {
                "wf_config": json.dumps(workflow_configurations)
            }
        )

        await session.commit()
        print(f"[SUCCESS] Deployed updated Akruti WhatsApp & No-Booking workflow to Definition {def_id}.")

if __name__ == "__main__":
    asyncio.run(main())
