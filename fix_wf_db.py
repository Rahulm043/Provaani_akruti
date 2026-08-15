import asyncio, json
from api.db import db_client
from sqlalchemy import text


async def main():
    rows = await db_client.execute_raw_query(
        "SELECT id, workflow_json, version_number, status FROM workflow_definitions WHERE workflow_id = 1 ORDER BY version_number DESC LIMIT 1"
    )
    row = rows[0]
    d = row["workflow_json"]

    # Remove node 1 and edge 1->2
    d["nodes"] = [n for n in d["nodes"] if n["id"] != "1"]
    d["edges"] = [e for e in d["edges"] if e["source"] != "1" and e["target"] != "1"]

    # Set node 2 as start
    for n in d["nodes"]:
        if n["id"] == "2":
            n["type"] = "startCall"
            n["data"]["is_start"] = True
            n["data"]["delayed_start"] = False
            # Prepend greeting to prompt as first instruction
            n["data"]["prompt"] = (
                'IMPORTANT - Your first and ONLY action when the call starts is to say: "Namaskar, ami Riya bolchhi. Provani AI theke calling korchhi. Aapni ki ektu kotha bolte parben?" '
                "Do NOT call any functions or transitions before greeting. After saying the greeting, wait for the user to respond.\n\n"
                + n["data"]["prompt"]
            )

    d["start_node_id"] = "2"

    async with db_client.async_session() as session:
        await session.execute(
            text("UPDATE workflow_definitions SET workflow_json = :wf WHERE id = :id"),
            {"wf": json.dumps(d), "id": row["id"]},
        )
        await session.commit()
    print(f"Updated version {row['version_number']} (id={row['id']})")


asyncio.run(main())
