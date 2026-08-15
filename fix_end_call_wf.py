import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def main():
    async with db_client.async_session() as session:
        # Get published definition
        res = await session.execute(text("SELECT id, workflow_json, workflow_configurations FROM workflow_definitions WHERE workflow_id = 1 AND status = 'published';"))
        row = res.first()
        wf_json = row.workflow_json
        wd_conf = row.workflow_configurations

        # Get end_call tool UUID
        tool_res = await session.execute(text("SELECT tool_uuid FROM tools WHERE name = 'end_call' AND organization_id = 1;"))
        tool_row = tool_res.first()
        end_call_uuid = tool_row.tool_uuid if tool_row else "e5528490-e765-401c-9be2-ae4c8d0eea57"
        print(f"Using end_call tool UUID: {end_call_uuid}")

        # Update Nodes
        for n in wf_json.get("nodes", []):
            if n.get("id") == "2":
                n["data"]["tool_uuids"] = [end_call_uuid]
                
                end_instructions = """

## Ending the Call & Disconnecting
When the caller says goodbye, thanks you, confirms they have no more questions, or wants to hang up (e.g. 'bye', 'thank you', 'dhanyawad', 'theek hai', 'thikache', 'rakhchhi', 'goodbye'):
1. Say ONE short, warm polite closing sentence:
   - Hindi: 'बात करने के लिए धन्यवाद! आकृति एस्थेटिक्स में आपका दिन शुभ हो।'
   - Bengali: 'আকৃতি এস্থেটিক্সে যোগাযোগ করার জন্য ধন্যবাদ। ভালো থাকবেন!'
   - English: 'Thank you for calling Akruti Aesthetics. Have a wonderful day!'
2. IMMEDIATELY call the `end_call` tool to disconnect the phone call. Do NOT ramble or speak again after that."""
                
                if "## Ending the Call & Disconnecting" not in n["data"]["prompt"]:
                    n["data"]["prompt"] += end_instructions

            if n.get("id") == "3":
                n["type"] = "endCall"
                n["data"]["is_end"] = True
                n["data"]["prompt"] = "NODE 3 — End Call\n\nCall is finished. Disconnect now."

        # Update Edges
        for e in wf_json.get("edges", []):
            if e.get("source") == "2" and e.get("target") == "3":
                e["data"] = {
                    "condition": "The caller says goodbye, thank you, or indicates they want to end the call.",
                    "label": "End Call"
                }

        # Save to DB without updated_at column
        await session.execute(
            text("""
                UPDATE workflow_definitions 
                SET workflow_json = :wf_json,
                    status = 'published'
                WHERE id = :id;
            """),
            {"wf_json": json.dumps(wf_json), "id": row.id}
        )

        await session.commit()
        print("[SUCCESS] Workflow 1 updated: Attached `end_call` tool and configured instant disconnect.")

if __name__ == "__main__":
    asyncio.run(main())
