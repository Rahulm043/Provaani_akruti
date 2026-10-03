import os, requests, json
from dotenv import load_dotenv

load_dotenv()
key = os.getenv('VERCEL_AI_API_KEY')
headers = {
    'Authorization': f'Bearer {key}',
    'ai-gateway-auth-method': 'api-key',
    'ai-gateway-protocol-version': '0.0.1',
}
r = requests.get('https://ai-gateway.vercel.sh/v4/ai/config', headers=headers)
data = r.json()
for m in data.get('models', []):
    if m['id'] in ['google/gemini-3.8-flash-lite-tts', 'google/gemini-3.8-flash-tts']:
        print(json.dumps(m, indent=2))
