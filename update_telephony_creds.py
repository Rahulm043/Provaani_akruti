import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def main():
    async with db_client.async_session() as session:
        # 1. Unset default on all configs first
        await session.execute(
            text("UPDATE telephony_configurations SET is_default_outbound = false WHERE organization_id = 1;")
        )

        # 2. Update telephony config 2 to Plivo MAN2EWNZFLNTATYZUXOS
        creds = {
            "auth_id": "MAN2EWNZFLNTATYZUXOS",
            "auth_token": "MjcxOGM0ZGYtNmY1YS00YjI4LTU2ZDYtNWU2M2I2",
            "application_id": "88306597238709575"
        }
        await session.execute(
            text("""
                UPDATE telephony_configurations 
                SET credentials = :creds,
                    is_default_outbound = true
                WHERE id = 2;
            """),
            {"creds": json.dumps(creds)}
        )

        # 3. Update phone numbers table
        await session.execute(
            text("""
                UPDATE telephony_phone_numbers 
                SET telephony_configuration_id = 2,
                    address = '+918031336640',
                    address_normalized = '+918031336640',
                    label = 'Akruti Aesthetics',
                    inbound_workflow_id = 1,
                    is_active = true,
                    is_default_caller_id = true
                WHERE id = 1;
            """)
        )

        # Add 918031336640 (without leading +)
        await session.execute(
            text("""
                INSERT INTO telephony_phone_numbers (organization_id, telephony_configuration_id, address, address_normalized, address_type, inbound_workflow_id, is_active, is_default_caller_id, extra_metadata, created_at, updated_at)
                VALUES (1, 2, '918031336640', '918031336640', 'pstn', 1, true, false, '{}', NOW(), NOW())
                ON CONFLICT (organization_id, address_normalized) DO UPDATE 
                SET inbound_workflow_id = 1, is_active = true;
            """)
        )

        await session.commit()

        print("[SUCCESS] Configured Telephony Credentials & Number Normalization variants in DB.")

if __name__ == "__main__":
    asyncio.run(main())
