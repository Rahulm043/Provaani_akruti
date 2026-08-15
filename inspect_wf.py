import asyncio, json
from api.db import db_client
from sqlalchemy import text

async def main():
    async with db_client.async_session() as session:
        res = await session.execute(text("SELECT id, workflow_json, workflow_configurations FROM workflow_definitions WHERE workflow_id = 1 AND status = 'published';"))
        row = res.first()
        d = row.workflow_json
        print("=== NODES ===")
        for n in d.get("nodes", []):
            print(f"Node ID: {n.get('id')} | Type: {n.get('type')} | Name: {n.get('data', {}).get('name')}")
            print(f"  Tool UUIDs: {n.get('data', {}).get('tool_uuids')}")
            print(f"  Prompt:\n{n.get('data', {}).get('prompt')}")
            print("---")
        print("=== EDGES ===")
        for e in d.get("edges", []):
            print(f"{e.get('source')} -> {e.get('target')} | id={e.get('id')} | label={e.get('label')} | condition={e.get('condition')}")
        print("=== TOOLS IN DB ===")
        t_res = await session.execute(text("SELECT id, uuid, name, type, config FROM tools WHERE organization_id = 1;"))
        for t in t_res:
            print(f"Tool ID: {t.id} | UUID: {t.uuid} | Name: {t.name} | Type: {t.type} | Config: {t.config}")

if __name__ == "__main__":
    asyncio.run(main())
