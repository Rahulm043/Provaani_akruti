import json
import asyncio
from api.db import db_client
from sqlalchemy import text

async def main():
    with open("/tmp/wf2_payload.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    wf2_id = data["wf2_id"]
    wf2_name = data["wf2_name"]
    wf2_uuid = data["wf2_uuid"]
    wf2_json = data["wf2_json"]
    wf2_config = data["wf2_config"]
    disposition_codes = data.get("disposition_codes") or {}
    template_context_vars = data.get("template_context_vars") or {}

    print(f"Upserting replica workflow: ID={wf2_id}, Name='{wf2_name}'")

    async with db_client.async_session() as session:
        # 1. Ensure Workflow 2 row exists (initially released_definition_id = null to avoid FK error)
        res = await session.execute(text("SELECT id FROM workflows WHERE id = :id;"), {"id": wf2_id})
        exists = res.scalar() is not None

        if exists:
            print("Updating existing Workflow 2...")
            await session.execute(
                text("""
                    UPDATE workflows 
                    SET name = :name, 
                        workflow_definition = :wf_def,
                        workflow_configurations = :w_conf,
                        status = 'active'
                    WHERE id = :id;
                """),
                {
                    "id": wf2_id,
                    "name": wf2_name,
                    "wf_def": json.dumps(wf2_json),
                    "w_conf": json.dumps(wf2_config)
                }
            )
        else:
            print("Inserting new Workflow 2...")
            await session.execute(
                text("""
                    INSERT INTO workflows (
                        id, name, user_id, organization_id, status, workflow_uuid,
                        workflow_definition, workflow_configurations,
                        template_context_variables, call_disposition_codes,
                        released_definition_id, created_at
                    ) VALUES (
                        :id, :name, 1, 1, 'active', :uuid,
                        :wf_def, :w_conf,
                        :template_vars, :disp_codes,
                        NULL, NOW()
                    );
                """),
                {
                    "id": wf2_id,
                    "name": wf2_name,
                    "uuid": wf2_uuid,
                    "wf_def": json.dumps(wf2_json),
                    "w_conf": json.dumps(wf2_config),
                    "template_vars": json.dumps(template_context_vars),
                    "disp_codes": json.dumps(disposition_codes)
                }
            )

        # 2. Upsert workflow_definitions 2
        res_def = await session.execute(text("SELECT id FROM workflow_definitions WHERE id = :id;"), {"id": wf2_id})
        def_exists = res_def.scalar() is not None

        if def_exists:
            print("Updating existing Workflow Definition 2...")
            await session.execute(
                text("""
                    UPDATE workflow_definitions 
                    SET workflow_json = :wf_json,
                        workflow_configurations = :wd_conf,
                        status = 'published',
                        is_current = true
                    WHERE id = :id;
                """),
                {
                    "id": wf2_id,
                    "wf_json": json.dumps(wf2_json),
                    "wd_conf": json.dumps(wf2_config)
                }
            )
        else:
            print("Inserting new Workflow Definition 2...")
            await session.execute(
                text("""
                    INSERT INTO workflow_definitions (
                        id, workflow_id, is_current, status, version_number,
                        workflow_json, workflow_configurations,
                        template_context_variables, call_disposition_codes,
                        published_at, created_at
                    ) VALUES (
                        :id, :id, true, 'published', 1,
                        :wf_json, :wd_conf,
                        :template_vars, :disp_codes,
                        NOW(), NOW()
                    );
                """),
                {
                    "id": wf2_id,
                    "wf_json": json.dumps(wf2_json),
                    "wd_conf": json.dumps(wf2_config),
                    "template_vars": json.dumps(template_context_vars),
                    "disp_codes": json.dumps(disposition_codes)
                }
            )

        # 3. Update Workflow 2 with released_definition_id = 2
        await session.execute(
            text("UPDATE workflows SET released_definition_id = :id WHERE id = :id;"),
            {"id": wf2_id}
        )

        await session.commit()

    print("[SUCCESS] Workflow 2 (Gemini Live Replica) successfully deployed to database!")
    print("[NOTE] Workflow 1 remains completely untouched and active.")

if __name__ == "__main__":
    asyncio.run(main())
