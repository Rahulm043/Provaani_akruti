import os
import wave
import httpx

def main():
    # Read the downloaded /tmp/user148.wav
    with wave.open("/tmp/user148.wav", "rb") as w:
        rate = w.getframerate()
        nframes = w.getnframes()
        channels = w.getnchannels()
        sampwidth = w.getsampwidth()
        
        # Extract audio from 48s to 90s
        start_frame = int(48 * rate)
        end_frame = int(90 * rate)
        w.setpos(start_frame)
        frames = w.readframes(end_frame - start_frame)

    clip_path = "/tmp/user_clip.wav"
    with wave.open(clip_path, "wb") as out:
        out.setnchannels(channels)
        out.setsampwidth(sampwidth)
        out.setframerate(rate)
        out.writeframes(frames)

    clip_size = os.path.getsize(clip_path)
    print(f"Extracted clip {clip_path}: {clip_size} bytes (duration ~42s)")

    api_key = os.environ.get("SMALLEST_API_KEY", "sk_1a31ac802c8823395b7fbfa5b863bd68")
    
    # Try sending to Smallest AI STT endpoint
    try:
        with open(clip_path, "rb") as f:
            audio_bytes = f.read()
        
        headers = {"Authorization": f"Bearer {api_key}"}
        files = {"file": ("user_clip.wav", audio_bytes, "audio/wav")}
        data = {"model": "pulse", "language": "north_indic"}
        
        resp = httpx.post("https://waves-api.smallest.ai/api/v1/pulse/transcribe", headers=headers, files=files, data=data, timeout=30.0)
        print("Smallest AI HTTP Status:", resp.status_code)
        print("Smallest AI Response:", resp.text)
    except Exception as e:
        print(f"STT transcribe error: {e}")

if __name__ == "__main__":
    main()
