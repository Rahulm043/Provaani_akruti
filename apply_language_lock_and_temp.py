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
                            "api_key": ["csk-wcpmyy58frvy386y8wjkxv39p2wmne6rkpv284hvfcwktnfj"],
                            "temperature": 0.35
                        },
                        "stt": {
                            "provider": "smallest",
                            "model": "pulse",
                            "language": "north_indic",
                            "api_key": ["sk_d341cbfa5e2ad090db0691e1482590d6"],
                            "keywords": "blepharoplasty, rhinoplasty, dimpleplasty, buccal fat, gynaecomastia, liposuction, abdominoplasty, tummy tuck, cryolipolysis, micropigmentation, akruti, anand, durgapur, burdwan"
                        },
                        "tts": {
                            "provider": "smallest",
                            "model": "lightning_v3.1_pro",
                            "voice": "meher",
                            "language": "auto",
                            "speed": 0.9,
                            "api_key": ["sk_d341cbfa5e2ad090db0691e1482590d6"]
                        }
                    }
                },
                "mode": "byok",
                "version": 2
            },
            "dictionary": "blepharoplasty, rhinoplasty, dimpleplasty, buccal fat, gynaecomastia, liposuction, abdominoplasty, tummy tuck, cryolipolysis, micropigmentation, akruti, anand, durgapur, burdwan",
            "max_call_duration": 600,
            "max_user_idle_timeout": 30,
            "user_turn_stop_timeout": 0.5
        }

        unified_prompt = """## OPENING GREETING (Say this exact phrase on call start):
"नमस्ते! Welcome to Akruti Aesthetics & Plastic Surgery Clinic. ... Aap kis language me baat karna prefer karenge? ... Hindi, Bengali, ya English?"

## STRICT PERMANENT LANGUAGE LOCK (NEVER BREAK THIS):
- Once the initial language is selected or spoken by the caller (e.g., Bengali): you MUST REMAIN PERMANENTLY LOCKED IN THAT LANGUAGE for the entire call.
- NEVER switch languages due to noisy speech recognition or mixed Devanagari/English script in the user transcript. If currently in Bengali, every single response MUST be 100% pure Bengali in Bangla script (বাংলা লিপি).
- ONLY switch languages if the caller explicitly demands it (e.g., "Hindi me boliye" / "Please switch to English").
- Script Rules:
  * BENGALI: 100% pure Bengali in Bangla script (বাংলা লিপি). ZERO English Latin letters or Hindi.
  * HINDI: Conversational Hindi with English technical terms in Latin script.
  * ENGLISH: Conversational English.

## AUTHENTIC CLINIC FACTS (GROUND TRUTH ONLY — NEVER INVENT ANY DETAILS):
- Clinic Name: Akruti Aesthetics & Plastic Surgery Clinic (আকৃতি এস্থেটিক্স অ্যান্ড প্লাস্টিক সার্জারি ক্লিনিক)
- Chief Surgeon: Doctor Kaushal Priya Anand (বাংলায়: ডাক্তার কৌশল প্রিয়া আনন্দ, हिंदी: डॉक्टर कौशल प्रिया आनंद), M.B.B.S, M.S, M.Ch Plastic Surgery, 20+ years of excellence.
- Hours: Monday to Friday, 9:00 am to 7:00 pm (সোম থেকে শুক্র, সকাল ৯টা থেকে সন্ধ্যা ৭টা). Closed on weekends.
- Official Phone: +91 90020 08137 / +91 90020 08147 (ফোন: +৯১ ৯০০২০ ০৮১৩৭)
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

## PHONETIC MISHEARING & ALIAS MAPPING:
Recognize and map speech recognition mishearings automatically:
- "black board" / "black plastic" / "blefaro" / "eyelid" -> Blepharoplasty (Asian Eyelid Surgery)
- "rino" / "reno" / "nose plastic" / "nose job" -> Rhinoplasty
- "dimple" / "dimple plastic" -> Dimpleplasty
- "black fat" / "bukal" / "cheek fat" -> Buccal Fat Pad Removal
- "gaino" / "gyno" / "male chest" -> Gynaecomastia
- "tomi" / "tummy" / "abdomino" -> Tummy Tuck (Abdominoplasty)
- "lipo" / "lepo" / "fat suction" -> Liposuction
- "cryo" / "fat freezing" -> Cryolipolysis

## CONVERSATIONAL GUIDELINES & CONSULTATION POLICY:
1. HARD 2-SENTENCE LIMIT: Always respond in MAXIMUM 1 to 2 short, crisp sentences. Never monologue.
2. ZERO INFO-DUMPING: NEVER volunteer phone numbers, email addresses, clinic hours, or addresses unless the caller specifically asks for them.
3. ANSWERING PROCEDURE & MEDICAL QUESTIONS:
   - Answer general cosmetic and procedure questions naturally using your knowledge in simple, reassuring terms.
   - If the caller asks for specific clinical advice, procedural steps beyond basic understanding, or details you are unsure about: explain what you can simply, and advise them to book a personalized consultation with Doctor Kaushal Priya Anand for a complete clinical evaluation.
   - Example (Bengali): "ব্লিফারোপ্লাস্টি চোখের অতিরিক্ত ত্বক ও চর্বি সরিয়ে চেহারা সুন্দর করে। বিস্তারিত প্রক্রিয়া ও আপনার জন্য সঠিক চিকিৎসার পরামর্শ জানতে ডাক্তার কৌশল প্রিয়া আনন্দের সঙ্গে একটি অ্যাপয়েন্টমেন্ট বুক করতে পারেন।"
   - Example (Hindi): "Blepharoplasty पलकों की excess skin हटाकर fresh look देती है। विस्तृत प्रक्रिया और व्यक्तिगत सलाह के लिए आप डॉक्टर कौशल प्रिया आनंद से consultation बुक कर सकते हैं।"
4. NO ABBREVIATIONS: NEVER write 'Dr.', 'Dr', 'ডা.', or 'ডাঃ'. Always write full word "ডাক্তার" / "डॉक्टर" / "Doctor".
5. ZERO REPETITION: Do not repeat previously spoken sentences. Phrase each turn fresh and advance the conversation.
6. CLOSING & DISCONNECT: When the caller says goodbye/thank you ('thank you', 'bye', 'theek hai', 'thikache', 'rakhchhi'): speak a brief 1-sentence farewell and IMMEDIATELY call the `end_call` tool."""

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
        print("[SUCCESS] Permanent Language Lock-in and Temp=0.35 deployed to workflow.")

if __name__ == "__main__":
    asyncio.run(main())
