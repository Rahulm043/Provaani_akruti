import asyncio
import json
from api.db import db_client
from api.routes.campaign import compile_unified_prompt
from sqlalchemy import text

async def main():
    async with db_client.async_session() as session:
        # 1. Fetch active campaign settings
        res = await session.execute(
            text("SELECT value FROM organization_settings WHERE organization_id = 1 AND key = 'campaign_settings';")
        )
        row = res.first()
        settings = json.loads(row[0]) if row and row[0] else {}
        
        # 2. Compile unified prompt with latest rules & DTMF instructions
        new_prompt = compile_unified_prompt(settings)
        print(f"Compiled unified prompt length: {len(new_prompt)} chars")
        print("\n--- Prompt Preview (first 400 chars) ---\n" + new_prompt[:400] + "\n...")
        
        # 3. Update Workflow 1 start node
        res_wf = await session.execute(text("SELECT definition FROM workflows WHERE id = 1;"))
        wf_row = res_wf.first()
        if wf_row:
            wf_def = json.loads(wf_row[0])
            for node in wf_def.get("nodes", []):
                if node.get("data", {}).get("is_start") or node.get("id") == "1":
                    node["data"]["prompt"] = new_prompt
                    print(f"Updated node '{node.get('data', {}).get('name')}' prompt.")
            
            await session.execute(
                text("UPDATE workflows SET definition = :def, updated_at = NOW() WHERE id = 1;"),
                {"def": json.dumps(wf_def)}
            )
            await session.commit()
            print("Successfully saved updated prompt to Workflow 1 in database!")

if __name__ == "__main__":
    asyncio.run(main())
