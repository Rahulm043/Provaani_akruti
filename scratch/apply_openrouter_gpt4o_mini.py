import asyncio
import json
from api.db import db_client
from sqlalchemy import text

OPENROUTER_KEY = "OPENROUTER_API_KEY_PLACEHOLDER"

TARGET_LLM = {
    "provider": "openrouter",
    "model": "openai/gpt-4o-mini",
    "base_url": "https://openrouter.ai/api/v1",
    "api_key": [OPENROUTER_KEY],
    "temperature": 0.1
}

async def main():
    async with db_client.async_session() as session:
        # 1. Update published workflow definition (id=1)
        res = await session.execute(text("SELECT id, workflow_configurations FROM workflow_definitions WHERE workflow_id = 1;"))
        rows = res.fetchall()
        for r in rows:
            def_id = r[0]
            config = r[1]
            if isinstance(config, str):
                config = json.loads(config)
            
            if 'model_configuration_v2_override' in config:
                config['model_configuration_v2_override']['byok']['pipeline']['llm'] = TARGET_LLM
                await session.execute(
                    text("UPDATE workflow_definitions SET workflow_configurations = :cfg WHERE id = :id;"),
                    {"cfg": json.dumps(config), "id": def_id}
                )
                print(f"[OK] Updated workflow_definition ID {def_id} with {TARGET_LLM['model']} ({TARGET_LLM['provider']})")

        # 2. Update active workflow (id=1)
        res_wf = await session.execute(text("SELECT id, workflow_configurations FROM workflows WHERE id = 1;"))
        wf_rows = res_wf.fetchall()
        for r in wf_rows:
            wf_id = r[0]
            config = r[1]
            if isinstance(config, str):
                config = json.loads(config)
            
            if 'model_configuration_v2_override' in config:
                config['model_configuration_v2_override']['byok']['pipeline']['llm'] = TARGET_LLM
                await session.execute(
                    text("UPDATE workflows SET workflow_configurations = :cfg WHERE id = :id;"),
                    {"cfg": json.dumps(config), "id": wf_id}
                )
                print(f"[OK] Updated workflow ID {wf_id} with {TARGET_LLM['model']} ({TARGET_LLM['provider']})")

        # 3. Update organization_configurations if key exists
        res_org = await session.execute(text("SELECT value FROM organization_configurations WHERE key = 'MODEL_CONFIGURATION_V2' AND organization_id = 1;"))
        org_row = res_org.first()
        if org_row:
            org_cfg = org_row[0]
            if isinstance(org_cfg, str):
                org_cfg = json.loads(org_cfg)
            if 'byok' in org_cfg and 'pipeline' in org_cfg['byok']:
                org_cfg['byok']['pipeline']['llm'] = TARGET_LLM
                await session.execute(
                    text("UPDATE organization_configurations SET value = :val WHERE key = 'MODEL_CONFIGURATION_V2' AND organization_id = 1;"),
                    {"val": json.dumps(org_cfg)}
                )
                print(f"[OK] Updated organization_configurations MODEL_CONFIGURATION_V2")

        await session.commit()
        print("[SUCCESS] Workflow 1 LLM successfully switched to openai/gpt-4o-mini via OpenRouter!")

if __name__ == "__main__":
    asyncio.run(main())
