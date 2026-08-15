import json
import asyncio
from api.db import db_client
from sqlalchemy import text

async def main():
    with open("wf6_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    name = data["name"]
    w_conf = data.get("w_conf") or {}
    wf_json = data["wf_json"]
    wd_conf = data.get("wd_conf") or {}

    print(f"Applying workflow: {name}")

    async with db_client.async_session() as session:
        # 1. Update Workflow 1
        await session.execute(
            text("""
                UPDATE workflows 
                SET name = :name, 
                    workflow_configurations = :w_conf,
                    status = 'active'
                WHERE id = 1;
            """),
            {"name": name, "w_conf": json.dumps(w_conf)}
        )

        # 2. Update Workflow Definition 1
        await session.execute(
            text("""
                UPDATE workflow_definitions 
                SET workflow_json = :wf_json,
                    workflow_configurations = :wd_conf,
                    status = 'published'
                WHERE id = 1;
            """),
            {"wf_json": json.dumps(wf_json), "wd_conf": json.dumps(wd_conf)}
        )

        # 3. Clean up any other definitions and workflows
        await session.execute(text("DELETE FROM workflow_definitions WHERE id != 1;"))
        await session.execute(text("DELETE FROM workflows WHERE id != 1;"))

        # 4. Link Phone Number to Inbound Workflow 1
        await session.execute(
            text("UPDATE telephony_phone_numbers SET inbound_workflow_id = 1 WHERE address_normalized LIKE '%8065951924%';")
        )

        # 5. Set Organization Model Config to match Pipeline
        if "model_configuration_v2_override" in wd_conf:
            await session.execute(
                text("""
                    UPDATE organization_configurations 
                    SET value = :val 
                    WHERE key = 'MODEL_CONFIGURATION_V2' AND organization_id = 1;
                """),
                {"val": json.dumps(wd_conf["model_configuration_v2_override"])}
            )

        await session.commit()

    print("[SUCCESS] Workflow 6 (Akruti Aesthetics - Smallest AI TTS) is now Workflow 1.")
    print("[SUCCESS] Phone number +918065951924 is linked to Workflow 1 for inbound calls.")

if __name__ == "__main__":
    asyncio.run(main())
