import asyncio, secrets
from api.db.db_client import async_session
from sqlalchemy import text


async def main():
    key = "dgr_" + secrets.token_urlsafe(32)
    async with async_session() as session:
        await session.execute(
            text(
                "INSERT INTO api_keys (name, key, organization_id, created_at, updated_at) VALUES (:name, :key, :org_id, NOW(), NOW())"
            ),
            {"name": "custom-ui", "key": key, "org_id": 1},
        )
        await session.commit()
        print(f"API Key: {key}")


asyncio.run(main())
