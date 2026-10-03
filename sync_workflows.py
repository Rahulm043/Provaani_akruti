"""
Synchronize Workflow 1 and Workflow 4 with the compact, low-latency prompt,
branch-level operating hours, strict no-booking policy, strict language lock,
reliable end_call trigger, and Smallest AI TTS.
"""

import asyncio
import json
from sqlalchemy import text
from api.db import db_client
from api.services.prompt_compiler import compile_unified_prompt, DEFAULT_BRANCH_SCHEDULE

REQUIRED_TOOLS = [
    "e5528490-e765-401c-9be2-ae4c8d0eea57",  # end_call
    "a99a0879-98ab-44e5-9e1d-e56d3e029ff9",  # transfer_call
    "b72e905a-5942-4f9e-a228-48b0c411c521",  # send_whatsapp
]

async def sync():
    async with db_client.async_session() as session:
        # 1. Update end_call description in tools table for better function-calling salience
        await session.execute(
            text("""
                UPDATE tools 
                SET description = 'End and hang up the phone call immediately. Call this whenever the user says goodbye, thank you, is done, is busy, or indicates they want to hang up.'
                WHERE name = 'end_call';
            """)
        )
        print("Updated end_call tool description in tools table.")

        # 2. Fetch clinic settings
        res = await session.execute(
            text("SELECT value FROM organization_configurations WHERE organization_id = 1 AND key = 'clinic_settings';")
        )
        row = res.first()
        if row and row[0]:
            settings = row[0] if isinstance(row[0], dict) else json.loads(row[0])
        else:
            settings = {}

        # Ensure appointment_config has booking disabled and default 10 AM to 7 PM hours
        if not settings.get("appointment_config"):
            settings["appointment_config"] = {"enabled": True, "allow_booking": False, "schedule": {}}
        settings["appointment_config"]["enabled"] = True
        settings["appointment_config"]["allow_booking"] = False

        sched = settings["appointment_config"].get("schedule", {})
        branches = settings.get("branches", [])
        for b in branches:
            b_id = b.get("id")
            if b_id and (b_id not in sched or not sched[b_id]):
                sched[b_id] = DEFAULT_BRANCH_SCHEDULE
        settings["appointment_config"]["schedule"] = sched

        # Persist updated clinic_settings
        await session.execute(
            text("""
                UPDATE organization_configurations
                SET value = :val, updated_at = NOW()
                WHERE organization_id = 1 AND key = 'clinic_settings';
            """),
            {"val": json.dumps(settings)},
        )
        print("Updated organization_configurations with Phase 1 clinic timings.")
        
        # 3. Compile prompt
        compiled_prompt = compile_unified_prompt(settings)
        print(f"Compiled prompt length: {len(compiled_prompt)} characters")
        print("\n--- NEW COMPACT PROMPT WITH TIMINGS ---\n" + compiled_prompt + "\n----------------------------------------\n")
        
        # 4. Fetch Workflow 1 definition & config
        res_wf = await session.execute(
            text("SELECT workflow_definition, workflow_configurations FROM workflows WHERE id = 1;")
        )
        wf_row = res_wf.first()
        if not wf_row:
            raise RuntimeError("Workflow 1 not found in database!")
            
        wf_def = wf_row[0] if isinstance(wf_row[0], dict) else json.loads(wf_row[0])
        wf_cfg = wf_row[1] if isinstance(wf_row[1], dict) else json.loads(wf_row[1])
        
        # 5. Standardize model config to GPT-4o-mini + Smallest AI (meher, 0.9)
        wf_cfg["model_configuration_v2_override"]["byok"]["pipeline"]["llm"] = {
            "provider": "openrouter",
            "model": "openai/gpt-4o-mini",
            "base_url": "https://openrouter.ai/api/v1",
            "api_key": ["OPENROUTER_API_KEY_PLACEHOLDER"],
            "temperature": 0.1,
        }
        wf_cfg["model_configuration_v2_override"]["byok"]["pipeline"]["stt"] = {
            "provider": "smallest",
            "model": "pulse",
            "language": "north_indic",
            "api_key": ["SMALLEST_AI_KEY_PLACEHOLDER"],
            "keywords": "blepharoplasty, rhinoplasty, dimpleplasty, buccal fat, gynaecomastia, liposuction, abdominoplasty, tummy tuck, cryolipolysis, micropigmentation, akruti, anand, durgapur, burdwan, whatsapp",
        }
        wf_cfg["model_configuration_v2_override"]["byok"]["pipeline"]["tts"] = {
            "provider": "smallest",
            "model": "lightning_v3.1_pro",
            "voice": "meher",
            "language": "auto",
            "speed": 0.9,
            "api_key": ["SMALLEST_AI_KEY_PLACEHOLDER"],
        }
        
        # 6. Update prompt and tool UUIDs in workflow_definition
        for node in wf_def.get("nodes", []):
            if node.get("id") == "1" or node.get("data", {}).get("is_start"):
                node["data"]["prompt"] = compiled_prompt
                node["data"]["tool_uuids"] = REQUIRED_TOOLS
                node["data"]["name"] = "Akruti Receptionist"
                print(f"Updated node '{node.get('data', {}).get('name')}' with new prompt and tools.")
                
        # 7. Save identical state to workflows 1 and 4
        for wf_id in [1, 4]:
            await session.execute(
                text("""
                    UPDATE workflows
                    SET workflow_definition = :def,
                        workflow_configurations = :cfg,
                        status = 'active'
                    WHERE id = :id;
                """),
                {
                    "def": json.dumps(wf_def),
                    "cfg": json.dumps(wf_cfg),
                    "id": wf_id,
                }
            )
            print(f"Updated workflows table for id = {wf_id}")

        # 8. Save identical state to workflow_definitions 1 and 4
        for def_id in [1, 4]:
            await session.execute(
                text("""
                    UPDATE workflow_definitions
                    SET workflow_json = :def,
                        workflow_configurations = :cfg,
                        status = 'published',
                        is_current = true
                    WHERE id = :id;
                """),
                {
                    "def": json.dumps(wf_def),
                    "cfg": json.dumps(wf_cfg),
                    "id": def_id,
                }
            )
            print(f"Updated workflow_definitions table for id = {def_id}")

        await session.commit()
        print("\nAll workflows (1 & 4) and definitions (1 & 4) are now updated and synchronized!")

if __name__ == "__main__":
    asyncio.run(sync())
