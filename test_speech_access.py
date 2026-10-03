import os, requests, json
from dotenv import load_dotenv

load_dotenv()
key = os.getenv('VERCEL_AI_API_KEY')
google_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')

models_to_test = [
    'google/gemini-3.8-flash-lite-tts',
    'google/gemini-3.8-flash-tts',
    'openai/tts-1',
    'fish-audio/s2-pro',
]

for m in models_to_test:
    headers = {
        'Authorization': f'Bearer {key}',
        'ai-gateway-auth-method': 'api-key',
        'ai-gateway-protocol-version': '0.0.1',
        'ai-model-id': m,
        'ai-speech-model-specification-version': '4',
        'Content-Type': 'application/json'
    }
    payload = {
        'text': 'Hello, testing speech generation.',
        'voice': 'Kore' if 'gemini' in m else 'alloy'
    }
    r = requests.post('https://ai-gateway.vercel.sh/v4/ai/speech-model', headers=headers, json=payload)
    print(f'Model: {m} -> Status: {r.status_code}')
    print('  Resp:', r.text[:200])

# Also test if passing x-api-key or Google API key directly works:
headers_byok = {
    'Authorization': f'Bearer {key}',
    'ai-gateway-auth-method': 'api-key',
    'ai-gateway-protocol-version': '0.0.1',
    'ai-model-id': 'google/gemini-3.8-flash-lite-tts',
    'ai-speech-model-specification-version': '4',
    'x-api-key': google_key,
    'Content-Type': 'application/json'
}
r_byok = requests.post('https://ai-gateway.vercel.sh/v4/ai/speech-model', headers=headers_byok, json={'text': 'Hello', 'voice': 'Kore'})
print(f'BYOK Google Key -> Status: {r_byok.status_code}, Resp: {r_byok.text[:200]}')
