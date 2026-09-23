import os
import sys
import json
import httpx
import asyncio

# Load credentials from .env if present
env_file = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_file):
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN") or os.environ.get("FB_WHATSAOO_ACCESS_TOKEN", "")
PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "1273585869163196")
TEMPLATE_NAME = os.environ.get("WHATSAPP_TEMPLATE_NAME", "clinic_details")

async def test_send(recipient: str = "917044311109"):
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    print(f"=== Testing Meta WhatsApp Cloud API ===")
    print(f"Phone Number ID: {PHONE_NUMBER_ID}")
    print(f"Template Name:   {TEMPLATE_NAME}")
    print(f"Recipient:       {recipient}")

    for lang in ["en", "en_US"]:
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "template",
            "template": {
                "name": TEMPLATE_NAME,
                "language": {
                    "code": lang
                }
            }
        }
        print(f"\nAttempting dispatch with language code '{lang}'...")
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            print(f"HTTP Status: {resp.status_code}")
            try:
                data = resp.json()
                print(f"Response Body:\n{json.dumps(data, indent=2)}")
                if resp.status_code in (200, 201):
                    print(">>> SUCCESS! Message dispatched via Meta Cloud API! <<<")
                    return True
            except Exception:
                print(f"Raw Response: {resp.text}")

    return False

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "917044311109"
    asyncio.run(test_send(target))
