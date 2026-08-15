import asyncio, json, sys
from api.db import db_client


async def main():
    rows = await db_client.pool.fetch(
        "SELECT id, name, provider_type, auth_id, auth_secret, extra_config FROM telephony_configs WHERE organization_id = 1"
    )
    for r in rows:
        print(f"ID: {r['id']}")
        print(f"  Name: {r['name']}")
        print(f"  Provider: {r['provider_type']}")
        print(f"  Auth ID: {r['auth_id']}")
        print(f"  Auth Secret: {r['auth_secret']}")
        print(f"  Extra: {r['extra_config']}")
    await db_client.pool.close()


asyncio.run(main())
