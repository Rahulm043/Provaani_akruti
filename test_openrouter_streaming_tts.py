from run_ssh_cmd import run_ssh

code = """
import asyncio
from pipecat.services.openai.tts import OpenAITTSService, OpenAITTSSettings, VALID_VOICES

# Add Aoede and other Gemini voices to VALID_VOICES
for v in ['Aoede', 'Kore', 'Puck', 'Charon', 'Fenrir', 'Leda', 'Zephyr', 'Orus']:
    VALID_VOICES[v] = v
    VALID_VOICES[v.lower()] = v

async def test():
    tts = OpenAITTSService(
        api_key='OPENROUTER_API_KEY_PLACEHOLDER',
        base_url='https://openrouter.ai/api/v1',
        voice='Aoede',
        sample_rate=24000,
        settings=OpenAITTSSettings(
            model='google/gemini-3.8-flash-lite-tts',
            voice='Aoede',
        ),
    )
    tts._sample_rate = 24000
    print('Testing OpenAITTSService with OpenRouter google/gemini-3.8-flash-lite-tts...')
    frames = []
    text = 'নমস্কার! আকৃতি নান্দনিক ও প্লাস্টিক সার্জারি ক্লিনিকে আপনাকে স্বাগত।'
    async for frame in tts.run_tts(text, context_id='test-1'):
        frames.append(frame)
        audio_len = len(getattr(frame, 'audio', b''))
        print(f'Frame {len(frames)}: {type(frame).__name__} ({audio_len} bytes)')
    print(f'SUCCESS! Total frames: {len(frames)}')

if __name__ == '__main__':
    asyncio.run(test())
"""

escaped = code.replace('"', '\\"').replace('$', '\\$')
run_ssh(f'sudo docker exec provaani_akruti-api-1 python -c "{escaped}"')
