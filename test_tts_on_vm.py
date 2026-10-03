import asyncio
from run_ssh_cmd import run_ssh

script = """
import asyncio
from pipecat.services.google.tts import GeminiTTSService

async def run():
    print('Available voices:', getattr(GeminiTTSService, 'AVAILABLE_VOICES', []))
    tts = GeminiTTSService(
        api_key='GOOGLE_AI_STUDIO_KEY_PLACEHOLDER',
        sample_rate=24000,
        settings=GeminiTTSService.Settings(
            model='gemini-3.8-flash-lite-tts',
            voice='Aoede',
            language='en-IN',
        ),
    )
    tts._sample_rate = 24000
    frames = []
    text_to_speak = "নমস্কার! আকৃতি নান্দনিক ও প্লাস্টিক সার্জারি ক্লিনিকে আপনাকে স্বাগত।"
    async for frame in tts.run_tts(text_to_speak, context_id='test'):
        frames.append(frame)
        audio_len = len(getattr(frame, 'audio', b''))
        print(f'Frame {len(frames)}: {type(frame).__name__} ({audio_len} bytes)')
    print(f'Done! Total frames: {len(frames)}')

if __name__ == '__main__':
    asyncio.run(run())
"""

escaped_script = script.replace('"', '\\"').replace('$', '\\$')
cmd = f"""sudo docker exec provaani_akruti-api-1 python -c "{escaped_script}" """
run_ssh(cmd)
