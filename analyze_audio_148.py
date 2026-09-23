import boto3
import wave
import struct
import math

def main():
    s3 = boto3.client(
        "s3",
        endpoint_url="http://minio:9000",
        aws_access_key_id="minioadmin",
        aws_secret_access_key="46f14446fe9983cc8e77edcf854bcf523766003b737c2684",
    )

    for track in ["user", "bot", "mixed"]:
        key = f"recordings/148/{track}.wav" if track != "mixed" else "recordings/148.wav"
        try:
            resp = s3.get_object(Bucket="voice-audio", Key=key)
            data = resp["Body"].read()
            with wave.open(data if hasattr(data, "read") else None, "rb") as w:
                pass
        except:
            pass

    # Download user.wav to /tmp/user148.wav and inspect
    resp = s3.get_object(Bucket="voice-audio", Key="recordings/148/user.wav")
    with open("/tmp/user148.wav", "wb") as f:
        f.write(resp["Body"].read())

    with wave.open("/tmp/user148.wav", "rb") as w:
        channels = w.getnchannels()
        rate = w.getframerate()
        nframes = w.getnframes()
        duration = nframes / float(rate)
        print(f"user.wav duration: {duration:.2f}s, channels: {channels}, rate: {rate}, nframes: {nframes}")

        # Let's inspect RMS energy every 5 seconds
        chunk_frames = rate * 5
        frames_read = 0
        idx = 0
        while frames_read < nframes:
            read_count = min(chunk_frames, nframes - frames_read)
            raw = w.readframes(read_count)
            frames_read += read_count
            # compute RMS
            count = len(raw) // 2
            if count > 0:
                shorts = struct.unpack(f"<{count}h", raw)
                sum_sq = sum(s * s for s in shorts)
                rms = math.sqrt(sum_sq / count)
                t_start = idx * 5
                t_end = t_start + (read_count / rate)
                print(f"  [{t_start:02d}s - {t_end:.1f}s] RMS energy: {rms:.1f}")
            idx += 1

    # Also inspect bot.wav
    resp_bot = s3.get_object(Bucket="voice-audio", Key="recordings/148/bot.wav")
    with open("/tmp/bot148.wav", "wb") as f:
        f.write(resp_bot["Body"].read())

    with wave.open("/tmp/bot148.wav", "rb") as w:
        rate = w.getframerate()
        nframes = w.getnframes()
        duration = nframes / float(rate)
        print(f"\nbot.wav duration: {duration:.2f}s, rate: {rate}, nframes: {nframes}")
        chunk_frames = rate * 5
        frames_read = 0
        idx = 0
        while frames_read < nframes:
            read_count = min(chunk_frames, nframes - frames_read)
            raw = w.readframes(read_count)
            frames_read += read_count
            count = len(raw) // 2
            if count > 0:
                shorts = struct.unpack(f"<{count}h", raw)
                sum_sq = sum(s * s for s in shorts)
                rms = math.sqrt(sum_sq / count)
                t_start = idx * 5
                t_end = t_start + (read_count / rate)
                print(f"  [{t_start:02d}s - {t_end:.1f}s] RMS energy: {rms:.1f}")
            idx += 1

if __name__ == "__main__":
    main()
