import asyncio, json
from api.db import db_client


async def main():
    rows = await db_client.execute_raw_query(
        "SELECT id, name, provider, credentials FROM telephony_configurations"
    )
    for r in rows:
        creds = (
            json.loads(r["credentials"])
            if isinstance(r["credentials"], str)
            else r["credentials"]
        )
        print(f"Name: {r['name']}, Provider: {r['provider']}")
        print(f"  Creds: {json.dumps(creds, indent=2)}")

    phones = await db_client.execute_raw_query(
        "SELECT id, phone_number, provider FROM telephony_phone_numbers"
    )
    for p in phones:
        print(f"Phone: {p['phone_number']} (provider: {p['provider']})")


asyncio.run(main())
