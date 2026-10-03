import asyncio
import json
import uuid
import asyncpg

DB_URL = "postgresql://postgres:764bb6070f6109033d7369b429ae6e6ac3aca26b84c1f84e@postgres:5432/postgres"

async def main():
    conn = await asyncpg.connect(DB_URL)

    # 1. Fetch Workflow 2
    wf2 = await conn.fetchrow("SELECT * FROM workflows WHERE id = 2")
    if not wf2:
        print("Workflow 2 not found!")
        return

    # 2. Fetch Workflow Definition 2
    wfd2 = await conn.fetchrow("SELECT * FROM workflow_definitions WHERE id = $1", wf2["released_definition_id"])
    if not wfd2:
        print("Workflow definition 2 not found!")
        return

    # 3. Build updated configurations for Vercel AI Gateway
    wf2_config = json.loads(wf2["workflow_configurations"]) if isinstance(wf2["workflow_configurations"], str) else dict(wf2["workflow_configurations"])
    config = json.loads(json.dumps(wf2_config))
    byok_realtime = config["model_configuration_v2_override"]["byok"]["realtime"]["realtime"]
    byok_realtime["provider"] = "google_realtime"
    byok_realtime["model"] = "google/gemini-3.8-live"
    byok_realtime["voice"] = "Aoede"
    byok_realtime["language"] = "bn"
    byok_realtime["api_key"] = ["VERCEL_AI_KEY_PLACEHOLDER"]

    config_json = json.dumps(config)
    wf_def_json = wf2["workflow_definition"] if isinstance(wf2["workflow_definition"], str) else json.dumps(wf2["workflow_definition"])
    tpl_ctx_json = wf2["template_context_variables"] if isinstance(wf2["template_context_variables"], str) else json.dumps(wf2["template_context_variables"])
    disp_codes_json = wf2["call_disposition_codes"] if isinstance(wf2["call_disposition_codes"], str) else json.dumps(wf2["call_disposition_codes"])

    wfd_json = wfd2["workflow_json"] if isinstance(wfd2["workflow_json"], str) else json.dumps(wfd2["workflow_json"])
    wfd_tpl_ctx = wfd2["template_context_variables"] if isinstance(wfd2["template_context_variables"], str) else json.dumps(wfd2["template_context_variables"])
    wfd_disp_codes = wfd2["call_disposition_codes"] if isinstance(wfd2["call_disposition_codes"], str) else json.dumps(wfd2["call_disposition_codes"])

    # Check if Workflow 3 already exists
    existing_wf3 = await conn.fetchrow("SELECT id FROM workflows WHERE id = 3")
    if existing_wf3:
        print("Workflow 3 already exists, updating...")
        await conn.execute("""
            UPDATE workflows
            SET name = 'Akruti - Vercel AI Gateway (Gemini 3.8 Live)',
                workflow_definition = $1::json,
                template_context_variables = $2::json,
                call_disposition_codes = $3::json,
                workflow_configurations = $4::json,
                status = 'active'
            WHERE id = 3
        """, wf_def_json, tpl_ctx_json, disp_codes_json, config_json)
    else:
        new_uuid = str(uuid.uuid4())
        print("Inserting Workflow 3...")
        await conn.execute("""
            INSERT INTO workflows (
                id, name, workflow_definition, created_at, user_id,
                template_context_variables, call_disposition_codes,
                organization_id, status, workflow_configurations, workflow_uuid
            ) VALUES (
                3, 'Akruti - Vercel AI Gateway (Gemini 3.8 Live)', $1::json, NOW(), $2,
                $3::json, $4::json, $5, 'active', $6::json, $7
            )
        """, wf_def_json, wf2["user_id"], tpl_ctx_json, disp_codes_json, wf2["organization_id"], config_json, new_uuid)

    # Check if Workflow Definition 3 exists
    existing_wfd3 = await conn.fetchrow("SELECT id FROM workflow_definitions WHERE id = 3")
    if existing_wfd3:
        print("Workflow Definition 3 already exists, updating...")
        await conn.execute("""
            UPDATE workflow_definitions
            SET workflow_id = 3,
                workflow_hash = $1,
                workflow_json = $2::json,
                is_current = true,
                status = 'published',
                version_number = 1,
                published_at = NOW(),
                workflow_configurations = $3::json,
                template_context_variables = $4::json,
                call_disposition_codes = $5::json
            WHERE id = 3
        """, wfd2["workflow_hash"], wfd_json, config_json, wfd_tpl_ctx, wfd_disp_codes)
    else:
        print("Inserting Workflow Definition 3...")
        await conn.execute("""
            INSERT INTO workflow_definitions (
                id, workflow_id, workflow_hash, workflow_json, created_at,
                is_current, status, version_number, published_at,
                workflow_configurations, template_context_variables, call_disposition_codes
            ) VALUES (
                3, 3, $1, $2::json, NOW(),
                true, 'published', 1, NOW(),
                $3::json, $4::json, $5::json
            )
        """, wfd2["workflow_hash"], wfd_json, config_json, wfd_tpl_ctx, wfd_disp_codes)

    # Ensure workflows.released_definition_id is set to 3
    await conn.execute("UPDATE workflows SET released_definition_id = 3 WHERE id = 3")

    # Reset sequences if necessary
    await conn.execute("SELECT setval('workflows_id_seq', (SELECT MAX(id) FROM workflows))")
    await conn.execute("SELECT setval('workflow_definitions_id_seq', (SELECT MAX(id) FROM workflow_definitions))")

    print("SUCCESS: Provisioned Workflow 3 & Definition 3!")
    rows = await conn.fetch("SELECT id, name, released_definition_id, workflow_uuid FROM workflows")
    for r in rows:
        print("Workflow:", dict(r))

    await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
