import asyncio
import json
import uuid
import asyncpg

DB_URL = "postgresql://postgres:764bb6070f6109033d7369b429ae6e6ac3aca26b84c1f84e@postgres:5432/postgres"

async def main():
    conn = await asyncpg.connect(DB_URL)

    # 1. Fetch Workflow 1
    wf1 = await conn.fetchrow("SELECT * FROM workflows WHERE id = 1")
    if not wf1:
        print("Workflow 1 not found!")
        await conn.close()
        return

    # 2. Fetch Workflow Definition 1
    wfd1 = await conn.fetchrow("SELECT * FROM workflow_definitions WHERE id = $1", wf1["released_definition_id"])
    if not wfd1:
        print("Workflow definition 1 not found!")
        await conn.close()
        return

    wf_def_json = wf1["workflow_definition"] if isinstance(wf1["workflow_definition"], str) else json.dumps(wf1["workflow_definition"])
    tpl_ctx_json = wf1["template_context_variables"] if isinstance(wf1["template_context_variables"], str) else json.dumps(wf1["template_context_variables"])
    disp_codes_json = wf1["call_disposition_codes"] if isinstance(wf1["call_disposition_codes"], str) else json.dumps(wf1["call_disposition_codes"])
    config_json = wf1["workflow_configurations"] if isinstance(wf1["workflow_configurations"], str) else json.dumps(wf1["workflow_configurations"])

    wfd_json = wfd1["workflow_json"] if isinstance(wfd1["workflow_json"], str) else json.dumps(wfd1["workflow_json"])
    wfd_tpl_ctx = wfd1["template_context_variables"] if isinstance(wfd1["template_context_variables"], str) else json.dumps(wfd1["template_context_variables"])
    wfd_disp_codes = wfd1["call_disposition_codes"] if isinstance(wfd1["call_disposition_codes"], str) else json.dumps(wfd1["call_disposition_codes"])
    wfd_config_json = wfd1["workflow_configurations"] if isinstance(wfd1["workflow_configurations"], str) else json.dumps(wfd1["workflow_configurations"])

    # 3. Check if Workflow 4 already exists
    existing_wf4 = await conn.fetchrow("SELECT id FROM workflows WHERE id = 4")
    if existing_wf4:
        print("Workflow 4 already exists, updating...")
        await conn.execute("""
            UPDATE workflows
            SET name = 'Akruti - Workflow 4 (Experiment Replica)',
                workflow_definition = $1::json,
                template_context_variables = $2::json,
                call_disposition_codes = $3::json,
                workflow_configurations = $4::json,
                status = 'active'
            WHERE id = 4
        """, wf_def_json, tpl_ctx_json, disp_codes_json, config_json)
    else:
        new_uuid = str(uuid.uuid4())
        print("Inserting Workflow 4...")
        await conn.execute("""
            INSERT INTO workflows (
                id, name, workflow_definition, created_at, user_id,
                template_context_variables, call_disposition_codes,
                organization_id, status, workflow_configurations, workflow_uuid
            ) VALUES (
                4, 'Akruti - Workflow 4 (Experiment Replica)', $1::json, NOW(), $2,
                $3::json, $4::json, $5, 'active', $6::json, $7
            )
        """, wf_def_json, wf1["user_id"], tpl_ctx_json, disp_codes_json, wf1["organization_id"], config_json, new_uuid)

    # 4. Check if Workflow Definition 4 exists
    existing_wfd4 = await conn.fetchrow("SELECT id FROM workflow_definitions WHERE id = 4")
    if existing_wfd4:
        print("Workflow Definition 4 already exists, updating...")
        await conn.execute("""
            UPDATE workflow_definitions
            SET workflow_id = 4,
                workflow_hash = $1,
                workflow_json = $2::json,
                is_current = true,
                status = 'published',
                version_number = 1,
                published_at = NOW(),
                workflow_configurations = $3::json,
                template_context_variables = $4::json,
                call_disposition_codes = $5::json
            WHERE id = 4
        """, wfd1["workflow_hash"], wfd_json, wfd_config_json, wfd_tpl_ctx, wfd_disp_codes)
    else:
        print("Inserting Workflow Definition 4...")
        await conn.execute("""
            INSERT INTO workflow_definitions (
                id, workflow_id, workflow_hash, workflow_json, created_at,
                is_current, status, version_number, published_at,
                workflow_configurations, template_context_variables, call_disposition_codes
            ) VALUES (
                4, 4, $1, $2::json, NOW(),
                true, 'published', 1, NOW(),
                $3::json, $4::json, $5::json
            )
        """, wfd1["workflow_hash"], wfd_json, wfd_config_json, wfd_tpl_ctx, wfd_disp_codes)

    # 5. Link released_definition_id = 4 on Workflow 4
    await conn.execute("UPDATE workflows SET released_definition_id = 4 WHERE id = 4")

    # 6. Reset sequences
    await conn.execute("SELECT setval('workflows_id_seq', (SELECT MAX(id) FROM workflows))")
    await conn.execute("SELECT setval('workflow_definitions_id_seq', (SELECT MAX(id) FROM workflow_definitions))")

    # 7. Activate Workflow 4 for inbound phone routing
    await conn.execute("UPDATE telephony_phone_numbers SET inbound_workflow_id = 4 WHERE organization_id = 1")

    print("[SUCCESS] Provisioned Workflow 4 replica of Workflow 1 and activated inbound routing!")

    rows = await conn.fetch("SELECT id, name, status, released_definition_id FROM workflows ORDER BY id")
    print("\n--- Workflows ---")
    for r in rows:
        print(dict(r))

    phones = await conn.fetch("SELECT id, address, inbound_workflow_id FROM telephony_phone_numbers WHERE organization_id = 1")
    print("\n--- Telephony Routing ---")
    for p in phones:
        print(dict(p))

    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
