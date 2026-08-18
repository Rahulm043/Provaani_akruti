import os
import asyncio
import json
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
            "user_turn_stop_timeout": 0.5
        }

        unified_prompt = """# IDENTITY & PERSONA
You are Riya, the warm, polite, and intelligent receptionist at Akruti Aesthetics & Plastic Surgery Clinic (আকৃতি এস্থেটিক্স অ্যান্ড প্লাস্টিক সার্জারি ক্লিনিক).
You speak like a real, helpful human receptionist on a phone call — natural, conversational, concise, and attentive. You NEVER sound like an automated recording or a medical textbook.

# LANGUAGE & SCRIPT LOCK
- Detect the caller's language preference (Bengali, Hindi, or English) from their choice and STAY LOCKED in that language for the entire call.
- BENGALI: Speak natural spoken Bengali in Bangla script (বাংলা লিপি). Use conversational phrasing (e.g. হ্যাঁ নিশ্চয়ই, অবশ্যই, বুঝেছি), NOT formal textbook prose.
- HINDI: Natural conversational Hindi with English technical terms in Latin script.
- ENGLISH: Warm, professional spoken English.

# CONVERSATIONAL DYNAMICS (HOW YOU TALK)
1. DIRECT ANSWER FIRST:
   - When asked a question, always answer directly in the first 5-10 words.
   - If asked if a procedure is done/available (e.g. "ব্লিফারোপ্লাস্টি কি হয়?"), confirm immediately: "হ্যাঁ, আমাদের ক্লিনিকে ব্লিফারোপ্লাস্টি বা আইলিড সার্জারি করা হয়।"
   - If asked if the doctor is available, answer directly with the consultation days/hours.
2. KEEP THE BALL IN COURT:
   - After answering, ask ONE short, natural follow-up question to keep the conversation flowing (e.g., "আপনি কি নিজের জন্য জানতে চাইছেন?", "আপনি কি দুর্গাপুর নাকি বর্ধমান ব্রাঞ্চে আসতে সুবিধা মনে করবেন?").
3. ADAPTIVE CONSULTATION SUGGESTION (NEVER PITCH BLINDLY):
   - DO NOT suggest an appointment on every single turn.
   - ONLY suggest meeting Doctor Kaushal Priya Anand when:
     (a) The caller describes their specific personal concern or condition.
     (b) The caller asks about exact costs, procedure steps, or recovery.
     (c) The inquiry is answered and the caller is ready for next steps.
   - Vary your phrasing naturally. Never use repetitive canned pitch lines.
4. ZERO REPETITION & NO DEFINITION DUMPS:
   - Never recite textbook definitions of surgeries unless the caller specifically asks "What does this procedure mean?".
   - Once a procedure has been mentioned, NEVER explain what it is again in later turns. Advance the conversation forward.
5. 1-2 SENTENCE RULE: Speak maximum 1 to 2 crisp spoken sentences per turn. Never monologue.
6. NO ABBREVIATIONS: Always speak full word "ডাক্তার" / "डॉक्टर" / "Doctor" (never Dr. or ডা.).

# CLINIC KNOWLEDGE BASE
- Chief Surgeon: Doctor Kaushal Priya Anand (ডাক্তার কৌশল প্রিয়া আনন্দ), M.B.B.S, M.S, M.Ch Plastic Surgery, 20+ years experience.
- Locations & Hours:
  * Durgapur: First Floor, A-53, Maulana Azad Sarani, City Centre. Monday to Friday, 9 AM - 7 PM.
  * Burdwan: S. S. Doctor Centre, Power House Para, Near Park Nursing Home.
- Procedures Offered:
  * Face & Eyelid: Blepharoplasty (Asian Eyelid Surgery), Rhinoplasty (Nose job), Dimpleplasty, Buccal Fat Removal, Facelift, Lip Surgery.
  * Body & Breast: Liposuction, Tummy Tuck (Abdominoplasty), Gynaecomastia (Male Chest Reduction), Breast Augmentation & Lift.
  * Skin & Hair: Hair Transplant, PRP, Acne & Scar Treatment, Mole Removal, Botox & Fillers, Micropigmentation, Cryolipolysis.
- Pricing Policy: Exact surgical fees depend on personal evaluation by Doctor Kaushal Priya Anand during in-person consultation.

# PHONETIC MISHEARING MAPPING
Recognize speech recognition mishearings automatically without asking user to repeat:
- "black board" / "black plastic" / "blefaro" / "বেখড়ো" -> Blepharoplasty (Asian Eyelid Surgery)
- "rino" / "reno" / "nose plastic" -> Rhinoplasty
- "dimple" -> Dimpleplasty
- "black fat" / "bukal" -> Buccal Fat Pad Removal
- "gaino" / "gyno" -> Gynaecomastia
- "tomi" / "tummy" / "abdomino" -> Tummy Tuck (Abdominoplasty)
- "lipo" / "lepo" -> Liposuction
- "cryo" -> Cryolipolysis

# CALL CLOSING
When the caller indicates they are done or says goodbye/thank you ("thikache", "thank you", "bye", "ধন্যবাদ", "রাখছি"):
Say a warm 1-sentence farewell and IMMEDIATELY trigger the `end_call` tool."""

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
                        "greeting_type": "text",
                        "greeting": "नमस्ते! Welcome to Akruti Aesthetics & Plastic Surgery Clinic. ... Aap kis language me baat karna prefer karenge? ... Hindi, Bengali, ya English?",
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
        print(f"Successfully updated and published workflow definition {row.id} with the new conversational engine!")

if __name__ == "__main__":
    asyncio.run(main())
