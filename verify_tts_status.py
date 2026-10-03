import asyncio
import json
from api.db import db_client
from sqlalchemy import text

async def check():
    async with db_client.async_session() as session:
        for wf_id in [1, 4]:
            res = await session.execute(text(f"SELECT id, name, workflow_configurations FROM workflows WHERE id = {wf_id};"))
            row = res.first()
            cfg = json.loads(row[2]) if isinstance(row[2], str) else row[2]
            tts = cfg.get("model_configuration_v2_override", {}).get("byok", {}).get("pipeline", {}).get("tts", {})
            print(f"WF {row[0]} ({row[1]}):")
            print(f"  Provider: {tts.get('provider')}")
            print(f"  Model:    {tts.get('model')}")
            print(f"  Voice:    {tts.get('voice')}")
            print(f"  Speed:    {tts.get('speed')}")
            print(f"  API Key:  {'Present' if tts.get('api_key') else 'None'}\n")

if __name__ == "__main__":
    asyncio.run(check())
