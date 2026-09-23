import os
import wave
import struct
import math

# Let's inspect the exact audio samples in /tmp/user148.wav between 50s and 85s
with wave.open("/tmp/user148.wav", "rb") as w:
    rate = w.getframerate()
    nframes = w.getnframes()
    print(f"Sample rate: {rate}, Total frames: {nframes}, Total duration: {nframes/rate:.2f}s")
    
    # Check 1-second intervals between 45s and 90s
    for sec in range(45, 90):
        w.setpos(sec * rate)
        raw = w.readframes(rate)
        count = len(raw) // 2
        shorts = struct.unpack(f"<{count}h", raw)
        rms = math.sqrt(sum(s * s for s in shorts) / count) if count else 0
        max_val = max(abs(s) for s in shorts) if count else 0
        if max_val > 500:
            print(f"Sec {sec:02d}-{sec+1:02d}s: RMS={rms:.1f}, MaxPeak={max_val}")

