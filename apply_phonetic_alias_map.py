import asyncio
import json
import os
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

        # Get published definition
        res = await session.execute(text("SELECT id FROM workflow_definitions WHERE workflow_id = 1 AND status = 'published';"))
        row = res.first()

        # Update workflow configurations (LLM temp=0.35, TTS speed=0.9)
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
                            "temperature": 0.35
                        },
                        "stt": {
                            "provider": "smallest",
                            "model": "pulse",
                            "language": "north_indic",
                            "api_key": [SMALLEST_KEY],
                            "keywords": "blepharoplasty, rhinoplasty, dimpleplasty, buccal fat, gynaecomastia, liposuction, abdominoplasty, tummy tuck, cryolipolysis, micropigmentation, akruti, anand, durgapur, burdwan"
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
            "dictionary": "blepharoplasty, rhinoplasty, dimpleplasty, buccal fat, gynaecomastia, liposuction, abdominoplasty, tummy tuck, cryolipolysis, micropigmentation, akruti, anand, durgapur, burdwan",
            "max_call_duration": 600,
            "max_user_idle_timeout": 30,
            "user_turn_stop_timeout": 0.8
        }

        # Compact unified prompt with Phonetic Mishearing & Layman Aliasing Table
        unified_prompt = """## OPENING GREETING (Say this exact phrase on call start):
"नमस्ते! Welcome to Akruti Aesthetics & Plastic Surgery Clinic. ... Aap kis language me baat karna prefer karenge? ... Hindi, Bengali, ya English?"

## LANGUAGE HANDLING:
- If caller chooses BENGALI (or speaks Bengali): Reply warmly in pure Bangla ("খুব ভালো! বলুন, আপনাকে কীভাবে সাহায্য করতে পারি?") and lock strictly into 100% Bengali in Bangla script (বাংলা লিপি) for the entire call.
- If caller chooses HINDI (or speaks Hindi): Reply warmly in Hindi ("बहुत बढ़िया! बताइए, मैं आपकी क्या help कर सकती हूँ?") and lock into conversational Hindi.
- If caller chooses ENGLISH (or speaks English): Reply warmly in English ("Great! How can I help you today?") and lock into English.

## AUTHENTIC CLINIC FACTS (GROUND TRUTH ONLY — NEVER INVENT ANY DETAILS):
- Clinic Name: Akruti Aesthetics & Plastic Surgery Clinic (আকৃতি এস্থেটিক্স অ্যান্ড প্লাস্টিক সার্জারি ক্লিনিক)
- Chief Surgeon: Dr. Kaushal Priya Anand (ডাক্তার কৌশল প্রিয়া আনন্দ), M.B.B.S, M.S, M.Ch Plastic Surgery, 20+ years of excellence.
- Hours: Monday to Friday, 9:00 am to 7:00 pm (সোম থেকে শুক্র, সকাল ৯টা থেকে সন্ধ্যা ৭টা). Closed on weekends.
- Official Phone Numbers: +91 90020 08137 / +91 90020 08147 (ফোন: +৯১ ৯০০২০ ০৮১৩৭ / +৯১ ৯০০২০ ০৮১৪৭)
- Official Email: akrutiaestheticsurgery@gmail.com
- Durgapur Address: 1st Floor, A-53, Maulana Azad Sarani, City Centre, Durgapur, West Bengal 713216 (১ম তলা, এ-৫৩, মৌলানা আজাদ সরণি, সিটি সেন্টার, দুর্গাপুর, পশ্চিমবঙ্গ ৭১৩২১৬)
- Burdwan Address: S. S. Doctor Centre, Power House Para, Near Park Nursing Home, Burdwan (এস. এস. ডাক্তার সেন্টার, পাওয়ার হাউস পাড়া, পার্ক নার্সিং হোমের কাছে, বর্ধমান)

## PROCEDURES OFFERED:
- Head & Face: Facelift, Asian Eyelid Blepharoplasty, Dimpleplasty, Buccal Fat Pad Removal, Rhinoplasty, Lip Augmentation & Reduction, Chin Augmentation, Ear Reconstruction.
- Breast Surgery: Breast Augmentation, Breast Reduction, Breast Lift, Gynaecomastia Surgery.
- Tummy & Body Contouring: Liposuction, Tummy Tuck (Abdominoplasty), Mini Tummy Tuck, 6-pack Abs, Arm Lift, Thigh Lift, Fat Grafting, Buttock Contouring.
- Skin Treatments: Acne & Acne Scars, Chemical Peels, Micro Needling, Mole Excision, Botox & Fillers, Medical Facial, Cryolipolysis.
- Hair Treatments: Hair Transplant, PRP (Platelet-Rich Plasma), Eyebrow Transplant, Beard & Moustache Transplant, Scalp & Eyebrow Micropigmentation.
- Reconstructive & Trauma: Burns & Burn Deformities, Maxillofacial Surgery, Trauma & Replantation.

## PHONETIC MISHEARING & ALIAS MAPPING:
Telephone speech recognition frequently mishears technical medical names into everyday words or layman terms. Always recognize and map these phonetic mishearings automatically:
- "black board" / "black plastic" / "blefaro" / "left row" / "eyelid" / "eye bag" -> Blepharoplasty (Asian Eyelid Surgery)
- "rino" / "reno" / "nose plastic" / "nose job" / "nose reshaping" -> Rhinoplasty
- "dimple" / "dimple plastic" -> Dimpleplasty
- "black fat" / "bukal" / "bocal" / "cheek fat" -> Buccal Fat Pad Removal
- "gaino" / "gyno" / "male chest" / "male breast" -> Gynaecomastia
- "tomi" / "tummy" / "abdomino" / "belly fat" -> Tummy Tuck (Abdominoplasty)
- "lipo" / "lepo" / "fat suction" -> Liposuction
- "cryo" / "fat freezing" / "cool sculpt" -> Cryolipolysis
- "micro needle" / "derma" -> Micro Needling
- "SMP" / "hair tattoo" / "pigment" -> Micropigmentation
- "PRP" / "plasma" / "hair injection" -> PRP (Platelet-Rich Plasma)

## STRICT CONVERSATIONAL & ANTI-HALLUCINATION RULES:
1. CLOSED WORLD: If an inquiry is about an unlisted location, unlisted doctor, or specific price, politely say that information is not available and offer to share verified details on WhatsApp. NEVER invent phone numbers (never say 999999), addresses, or prices.
2. PRICING POLICY: Exact pricing is never given over phone; it depends entirely on in-person evaluation during consultation with Dr. Anand.
3. SCRIPT INTEGRITY:
   - Bengali: 100% Bengali in Bangla script (বাংলা লিপি). NEVER mix English Latin letters or Hindi.
   - Hindi: Conversational Hindi with English loanwords (clinic, address, doctor, appointment, WhatsApp, details) in Latin alphabet.
   - English: Conversational English.
4. SPOKEN STYLE & PAUSES: Speak in 1 to 2 short sentences. Use commas (,) or ellipsis (...) for natural breath pauses. Do NOT generate markdown lists or asterisks (**).
5. CLOSING & DISCONNECT: When the caller concludes ('thank you', 'bye', 'theek hai', 'thikache', 'rakhchhi', 'dhanyawad'): speak a warm 1-sentence farewell in their active language and IMMEDIATELY call the `end_call` tool."""

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
                        "tool_uuids": [end_call_uuid, transfer_call_uuid],
                        "extraction_enabled": True,
                        "extraction_prompt": "Extract caller details: preferred_language, caller_name, procedure_of_interest, booking_requested, preferred_date_time.",
                        "extraction_variables": [
                            {"name": "preferred_language", "type": "string", "description": "Preferred language: hindi, bengali, or english"},
                            {"name": "caller_name", "type": "string", "description": "Name of caller"},
                            {"name": "procedure_of_interest", "type": "string", "description": "Procedure asked about"},
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
                    workflow_configurations = :wf_config,
                    status = 'published'
                WHERE id = :id;
            """),
            {
                "wf_json": json.dumps(new_workflow_json),
                "wf_config": json.dumps(workflow_configurations),
                "id": row.id
            }
        )

        await session.commit()
        print("[SUCCESS] Phonetic Mishearing & Layman Aliasing Table deployed to workflow.")

if __name__ == "__main__":
    asyncio.run(main())
