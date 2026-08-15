import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def main():
    async with db_client.async_session() as session:
        # Update end_call tool definition
        tool_def = {
            "schema_version": 1,
            "type": "end_call",
            "config": {
                "messageType": "custom",
                "customMessage": "Akruti Aesthetics & Plastic Surgery Clinic में call करने के लिए धन्यवाद! आपका दिन शुभ हो।",
                "audioRecordingId": None,
                "endCallReason": False,
                "endCallReasonDescription": None
            }
        }
        await session.execute(
            text("""
                UPDATE tools 
                SET definition = :definition,
                    updated_at = NOW()
                WHERE name = 'end_call' AND organization_id = 1;
            """),
            {"definition": json.dumps(tool_def)}
        )

        await session.commit()
        print("[SUCCESS] end_call tool updated with custom closing salutation for Akruti Aesthetics & Plastic Surgery Clinic.")

if __name__ == "__main__":
    asyncio.run(main())
