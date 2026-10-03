import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def check():
    async with db_client.async_session() as session:
        res = await session.execute(text("SELECT id, name, workflow_configurations, workflow_definition FROM workflows WHERE id = 1;"))
        row = res.first()
        if row:
            print("ID:", row[0])
            print("NAME:", row[1])
            cfg = json.loads(row[2]) if isinstance(row[2], str) else row[2]
            print("\nWORKFLOW_CONFIGURATIONS:")
            print(json.dumps(cfg, indent=2))
            
            wf_def = json.loads(row[3]) if isinstance(row[3], str) else row[3]
            nodes = wf_def.get("nodes", [])
            print(f"\nTOTAL NODES: {len(nodes)}")
            for n in nodes:
                ndata = n.get("data", {})
                print(f"Node id={n.get('id')}, name={ndata.get('name')}, is_start={ndata.get('is_start')}")
                p = ndata.get("prompt", "")
                print(f"Prompt length: {len(p)}")
                print("Prompt preview:\n", p[:300])

if __name__ == "__main__":
    asyncio.run(check())
