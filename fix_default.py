import asyncio
from sqlalchemy import text
from api.db import db_client


async def main():
    async with db_client.async_session() as session:
        await session.execute(
            text(
                "UPDATE telephony_configurations SET is_default_outbound = false WHERE id = 2"
            )
        )
        await session.execute(
            text(
                "UPDATE telephony_configurations SET is_default_outbound = true WHERE id = 1"
            )
        )
        await session.commit()
    print("OK")


asyncio.run(main())
