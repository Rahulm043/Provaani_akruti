import json
from run_ssh_cmd import run_ssh

code = """
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
        
        # 2. Update TTS configuration to provider: openai with OpenRouter base_url
        pipeline_cfg = wf_config.setdefault("model_configuration_v2_override", {}).setdefault("byok", {}).setdefault("pipeline", {})
        old_tts = pipeline_cfg.get("tts", {})
        print("Previous TTS config:", json.dumps(old_tts, indent=2))
        
        pipeline_cfg["tts"] = {
            "provider": "openai",
            "model": "google/gemini-3.8-flash-lite-tts",
            "base_url": "https://openrouter.ai/api/v1",
            "voice": "Aoede",
            "language": "en-IN",
            "speed": 1.0,
            "api_key": ["OPENROUTER_API_KEY_PLACEHOLDER"]
        }
        print("Updated TTS config:", json.dumps(pipeline_cfg["tts"], indent=2))

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

        # 5. Ensure inbound telephony line routes to Workflow 4
        await session.execute(
            text("UPDATE telephony_phone_numbers SET inbound_workflow_id = 4 WHERE address IN ('+918031825997', '918031825997', '8031825997', 'akruti');")
        )
        print("Confirmed telephony_phone_numbers: inbound_workflow_id = 4.")

        await session.commit()
        print("\\n✅ Successfully deployed Workflow 4 with valid schema for OpenRouter Gemini 3.8 Flash-Lite TTS!")

if __name__ == '__main__':
    asyncio.run(main())
"""

escaped = code.replace('"', '\\"').replace('$', '\\$')
run_ssh(f'sudo docker exec provaani_akruti-api-1 python -c "{escaped}"')
