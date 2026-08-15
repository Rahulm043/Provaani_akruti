import asyncio, json
from api.db import db_client


async def main():
    rows = await db_client.pool.fetch("SELECT * FROM telephony_configs")
    for r in rows:
        print(f"ID: {r['id']}, Provider: {r['provider_type']}")
        print(f"  Auth ID: {r['auth_id']}")
        print(
            f"  Auth Secret: {r['auth_secret'][:10]}... ({len(r['auth_secret'])} chars)"
        )
        extra = json.loads(r["extra_config"]) if r["extra_config"] else {}
        print(f"  Extra: {json.dumps(extra)}")
    await db_client.pool.close()


asyncio.run(main())
