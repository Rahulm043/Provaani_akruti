import asyncio, json
from api.db import db_client


async def main():
    rows = await db_client.execute_raw_query(
        "SELECT id, name, provider_type, auth_id, auth_secret, extra_config FROM telephony_configurations"
    )
    for r in rows:
        print(f"ID: {r['id']}")
        print(f"  Name: {r['name']}")
        print(f"  Provider: {r['provider_type']}")
        print(f"  Auth ID: {r['auth_id']}")
        secret = str(r["auth_secret"])
        print(f"  Auth Secret: {secret[:15]}... ({len(secret)} chars)")
        extra = json.loads(r["extra_config"]) if r["extra_config"] else {}
        print(f"  Extra: {json.dumps(extra)}")

    rows2 = await db_client.execute_raw_query(
        "SELECT id, phone_number, provider_type FROM telephony_phone_numbers"
    )
    for r in rows2:
        print(f"Phone: {r['phone_number']} (provider: {r['provider_type']})")


asyncio.run(main())
