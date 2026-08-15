import asyncio, json
from api.db import db_client


async def main():
    wf = await db_client.get_workflow(1, 1)
    if wf and wf.definition:
        d = wf.definition.workflow_json
        print("Nodes:")
        for n in d.get("nodes", []):
            print(f"  {n['id']}: {n['type']} - {n['data'].get('name', '?')}")
        print()
        print("Edges:")
        for e in d.get("edges", []):
            print(f"  {e['source']} -> {e['target']}")
        print()
        print("Start node:", d.get("start_node_id"))


asyncio.run(main())
