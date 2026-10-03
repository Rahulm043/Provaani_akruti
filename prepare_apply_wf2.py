import json

with open("wf2_payload.json", "r", encoding="utf-8") as f:
    p = json.load(f)

# SQL script with proper foreign key order
sql = f"""
-- 1. Upsert into workflows with released_definition_id = NULL first
INSERT INTO workflows (
    id, name, user_id, organization_id, status, workflow_uuid,
    workflow_definition, workflow_configurations,
    template_context_variables, call_disposition_codes,
    released_definition_id, created_at
) VALUES (
    2, '{p['wf2_name']}', 1, 1, 'active', '{p['wf2_uuid']}',
    '{json.dumps(p['wf2_json']).replace("'", "''")}'::json,
    '{json.dumps(p['wf2_config']).replace("'", "''")}'::json,
    '{json.dumps(p['template_context_vars']).replace("'", "''")}'::json,
    '{json.dumps(p['disposition_codes']).replace("'", "''")}'::json,
    NULL, NOW()
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    workflow_definition = EXCLUDED.workflow_definition,
    workflow_configurations = EXCLUDED.workflow_configurations,
    status = 'active';

-- 2. Upsert into workflow_definitions
INSERT INTO workflow_definitions (
    id, workflow_id, is_current, status, version_number,
    workflow_json, workflow_configurations,
    template_context_variables, call_disposition_codes,
    published_at, created_at
) VALUES (
    2, 2, true, 'published', 1,
    '{json.dumps(p['wf2_json']).replace("'", "''")}'::json,
    '{json.dumps(p['wf2_config']).replace("'", "''")}'::json,
    '{json.dumps(p['template_context_vars']).replace("'", "''")}'::json,
    '{json.dumps(p['disposition_codes']).replace("'", "''")}'::json,
    NOW(), NOW()
)
ON CONFLICT (id) DO UPDATE SET
    workflow_json = EXCLUDED.workflow_json,
    workflow_configurations = EXCLUDED.workflow_configurations,
    status = 'published',
    is_current = true;

-- 3. Update workflows released_definition_id
UPDATE workflows SET released_definition_id = 2 WHERE id = 2;
"""

with open("apply_wf2.sql", "w", encoding="utf-8") as f:
    f.write(sql)

print("Generated apply_wf2.sql successfully!")
