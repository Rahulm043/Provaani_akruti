import urllib.request
import json
import os

key = os.environ.get("VERCEL_AI_GATEWAY_KEY", "VERCEL_AI_KEY_PLACEHOLDER")
headers = {"Authorization": f"Bearer {key}"}

req = urllib.request.Request("https://ai-gateway.vercel.sh/v1/credits", headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        balance = float(data.get("balance", 0))
        total_used = float(data.get("total_used", 0))
        print(f"Vercel AI Gateway Current State:")
        print(f"  Total Used: ${total_used:.7f} (~INR {total_used * 86.5:.4f})")
        print(f"  Remaining Balance: ${balance:.7f}")
except Exception as e:
    print(f"Error checking credits: {e}")
