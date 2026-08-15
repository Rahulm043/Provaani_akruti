import asyncio, json
from api.db import db_client


async def main():
    rows = await db_client.execute_raw_query(
        "SELECT id, name, provider, credentials, is_default_outbound FROM telephony_configurations"
    )
    for r in rows:
        print(f"ID: {r['id']}")
        print(f"  Name: {r['name']}")
        print(f"  Provider: {r['provider']}")
        print(f"  Default Outbound: {r['is_default_outbound']}")
        creds = (
            json.loads(r["credentials"])
            if isinstance(r["credentials"], str)
            else r["credentials"]
        )
        print(f"  Credentials: {json.dumps(creds, default=str, indent=2)}")


asyncio.run(main())
