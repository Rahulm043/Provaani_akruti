import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def main():
    async with db_client.async_session() as session:
        # 1. Fetch current workflow 4 from workflows
        res_wf = await session.execute(text("SELECT workflow_configurations FROM workflows WHERE id = 4;"))
        wf_row = res_wf.first()
        if not wf_row or not wf_row[0]:
            print("Workflow 4 not found in workflows table!")
            return

        wf_config = json.loads(wf_row[0]) if isinstance(wf_row[0], str) else wf_row[0]
        
        # 2. Update TTS configuration to gemini-3.8-flash-lite-tts
        pipeline_cfg = wf_config.setdefault("model_configuration_v2_override", {}).setdefault("byok", {}).setdefault("pipeline", {})
        old_tts = pipeline_cfg.get("tts", {})
        print("Old TTS config:", json.dumps(old_tts, indent=2))
        
        pipeline_cfg["tts"] = {
            "provider": "google",
            "model": "gemini-3.8-flash-lite-tts",
            "voice": "Aoede",
            "language": "en-US",
            "speed": 1.0,
            "api_key": ["GOOGLE_AI_STUDIO_KEY_PLACEHOLDER"]
        }
        print("New TTS config:", json.dumps(pipeline_cfg["tts"], indent=2))

        # 3. Update workflows table
        await session.execute(
            text("UPDATE workflows SET workflow_configurations = :cfg WHERE id = 4;"),
            {"cfg": json.dumps(wf_config)}
        )
        print("Updated workflows table for ID 4.")

        # 4. Update workflow_definitions table
        res_wd = await session.execute(
            text("SELECT id, workflow_configurations FROM workflow_definitions WHERE workflow_id = 4 AND is_current = true;")
        )
        wd_row = res_wd.first()
        if wd_row:
            await session.execute(
                text("UPDATE workflow_definitions SET workflow_configurations = :cfg WHERE id = :id;"),
                {"cfg": json.dumps(wf_config), "id": wd_row[0]}
            )
            print(f"Updated workflow_definitions table for ID {wd_row[0]}.")

        await session.commit()
        print("\n✅ Successfully updated Workflow 4 TTS to gemini-3.8-flash-lite-tts!")

if __name__ == "__main__":
    asyncio.run(main())
