import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def main():
    async with db_client.async_session() as session:
        print("=== 1. Checking existing ARI telephony configurations ===")
        res = await session.execute(text("SELECT id, name, provider, inactive FROM telephony_configurations WHERE organization_id = 1 AND provider = 'ari';"))
        existing = res.first()

        ari_credentials = {
            "provider": "ari",
            "ari_endpoint": "http://dograhtest-asterisk:8088",
            "app_name": "dograh_app",
            "app_password": "c9a8b7e6f5d4c3b2a1",
            "ws_client_name": "dograh_ws",
            "from_numbers": ["+918031825997", "918031825997"]
        }

        if existing:
            config_id = existing.id
            await session.execute(
                text("UPDATE telephony_configurations SET credentials = :creds, inactive = false, name = 'Plivo Zentrunk via Asterisk ARI' WHERE id = :id;"),
                {"creds": json.dumps(ari_credentials), "id": config_id}
            )
            print(f"Updated existing ARI config ID {config_id}.")
        else:
            res = await session.execute(
                text("""
                    INSERT INTO telephony_configurations (organization_id, name, provider, inactive, credentials, created_at, updated_at)
                    VALUES (1, 'Plivo Zentrunk via Asterisk ARI', 'ari', false, :creds, NOW(), NOW())
                    RETURNING id;
                """),
                {"creds": json.dumps(ari_credentials)}
            )
            config_id = res.first()[0]
            print(f"Created new ARI config ID {config_id}.")

        print("=== 2. Updating telephony_phone_numbers mapping ===")
        numbers = ["+918031825997", "918031825997", "8031825997", "akruti"]
        for num in numbers:
            num_res = await session.execute(
                text("SELECT id FROM telephony_phone_numbers WHERE organization_id = 1 AND address_normalized = :num;"),
                {"num": num}
            )
            row = num_res.first()
            if row:
                await session.execute(
                    text("""
                        UPDATE telephony_phone_numbers 
                        SET telephony_configuration_id = :cfg_id,
                            inbound_workflow_id = 1,
                            is_active = true,
                            updated_at = NOW()
                        WHERE id = :id;
                    """),
                    {"cfg_id": config_id, "id": row.id}
                )
                print(f"Updated phone number {num} -> config {config_id}, workflow 1.")
            else:
                await session.execute(
                    text("""
                        INSERT INTO telephony_phone_numbers (
                            organization_id, telephony_configuration_id, address, address_normalized, 
                            address_type, country_code, label, inbound_workflow_id, is_active, 
                            is_default_caller_id, extra_metadata, created_at, updated_at
                        )
                        VALUES (
                            1, :cfg_id, :num, :num, 
                            'e164', 'IN', 'Akruti Asterisk SIP', 1, true, 
                            false, '{}'::json, NOW(), NOW()
                        );
                    """),
                    {"cfg_id": config_id, "num": num}
                )
                print(f"Inserted phone number {num} -> config {config_id}, workflow 1.")

        await session.commit()
        print("[SUCCESS] ARI Telephony Registered and Linked to Phone Numbers.")

if __name__ == "__main__":
    asyncio.run(main())
