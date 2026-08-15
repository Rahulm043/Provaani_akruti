import asyncio
from api.db import db_client
from sqlalchemy import text

async def main():
    async with db_client.async_session() as session:
        # Update phone number to +918031336640
        await session.execute(
            text("""
                UPDATE telephony_phone_numbers 
                SET address = '+918031336640',
                    address_normalized = '+918031336640',
                    label = 'Akruti Aesthetics',
                    inbound_workflow_id = 1,
                    is_active = true,
                    is_default_caller_id = true
                WHERE id = 1;
            """)
        )
        await session.commit()

        rows = await session.execute(text("SELECT id, address, address_normalized, inbound_workflow_id, is_active FROM telephony_phone_numbers;"))
        for r in rows:
            print("Updated Phone Number:", dict(r._mapping))

if __name__ == "__main__":
    asyncio.run(main())
