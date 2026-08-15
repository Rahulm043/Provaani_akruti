"""NeuTTS-2E TTS bridge - OpenAI-compatible streaming endpoint.

The model is loaded once at import time, before uvicorn starts its event
loop. NeuTTS2E's internals call asyncio.run(), which collides with a running
event loop - so lazy-loading inside request handlers throws
"Cannot run the event loop while another loop is running" and re-loads the
model on every request. Import-time loading avoids that.

Audio is streamed clause-by-clause as raw 24kHz 16-bit mono PCM, which is
what OpenAITTSService requests (response_format=pcm). The pipeline
transport resamples 24kHz down to the telephony output rate (8kHz) and the
Vobiz serializer converts PCM to mu-law, so we do NOT resample here.
"""

import asyncio
import io
import logging
import wave
from collections.abc import AsyncGenerator

import numpy as np
from fastapi import FastAPI, Request
from fastapi.responses import Response, StreamingResponse
from neutts import NeuTTS2E
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("neutts-bridge")

SAMPLE_RATE = 24000

# Map OpenAI voice names (sent by OpenAITTSService after VALID_VOICES lookup)
# to NeuTTS-2E speakers. OpenAITTSService rejects voices not in VALID_VOICES,
# so the Dograh config MUST use one of: alloy, echo, fable, onyx, nova,
# shimmer, ash, ballad, cedar, coral, marin, sage, verse.
SPEAKER_MAP = {
    "alloy": "emily",
    "nova": "emily",
    "echo": "paul",
    "onyx": "steven",
    "fable": "sophie",
    "shimmer": "sophie",
    "emily": "emily",
    "paul": "paul",
    "steven": "steven",
    "sophie": "sophie",
}

# Load + pre-warm the model once, before the event loop exists.
logger.info("Loading NeuTTS-2E model (Q4 GGUF)...")
_tts = NeuTTS2E()
_ = _tts.infer("Hello.", speaker="emily", emotion="neutral")
logger.info("NeuTTS-2E loaded and warmed up")

# Serialize inference: NeuTTS-2E is not safe for concurrent infer calls and
# on 2 vCPU parallel runs would thrash anyway.
_infer_lock = asyncio.Lock()

app = FastAPI()


def split_into_clauses(text: str, min_words: int = 4) -> list:
    """Split text into semantic clauses to get audio out incrementally."""
    text = text.strip()
    if not text:
        return []

    clauses = []
    buffer = ""
    for word in text.split():
        buffer += word + " "
        has_punct = any(p in word for p in ".,!?;:—")
        word_count = len(buffer.strip().split())
        if (has_punct and word_count >= 1) or word_count >= min_words:
            clauses.append(buffer.strip())
            buffer = ""

    if buffer.strip():
        if clauses and len(buffer.strip().split()) < 2:
            clauses[-1] += " " + buffer.strip()
        else:
            clauses.append(buffer.strip())

    return clauses


def _to_pcm(samples: np.ndarray) -> bytes:
    pcm = np.clip(samples, -1.0, 1.0)
    return (pcm * 32767).astype("<i2").tobytes()


async def _infer(clause: str, speaker: str, emotion: str) -> np.ndarray:
    async with _infer_lock:
        return await asyncio.to_thread(
            _tts.infer, text=clause, speaker=speaker, emotion=emotion
        )


async def stream_pcm(
    text: str, voice: str, emotion: str
) -> AsyncGenerator[bytes, None]:
    """Yield 24kHz PCM bytes clause-by-clause as each is synthesized."""
    speaker = SPEAKER_MAP.get(voice, "emily")
    clauses = split_into_clauses(text, min_words=4) or [text]
    logger.info(
        f"Streaming {len(clauses)} clauses voice={speaker} emotion={emotion} "
        f"({len(text)} chars)"
    )
    for i, clause in enumerate(clauses):
        try:
            samples = await _infer(clause, speaker, emotion)
            logger.debug(f"Clause {i + 1}/{len(clauses)}: {len(samples)} samples")
        except Exception as e:
            logger.error(
                f"Clause {i + 1}/{len(clauses)} failed ({clause[:50]}...): {e}"
            )
            continue
        yield _to_pcm(samples)
    logger.info(f"Done streaming {len(clauses)} clauses")


@app.post("/v1/audio/speech")
async def openai_tts(request: Request):
    body = await request.json()
    text = (body.get("input") or "").strip()
    voice = body.get("voice", "alloy")
    fmt = body.get("response_format", "pcm")
    emotion = body.get("emotion") or "neutral"
    # OpenAITTSService puts the model id in `model`; don't treat it as emotion.
    if emotion in ("tts-1", "tts-1-hd", "gpt-4o-mini-tts", "neutts-2e"):
        emotion = "neutral"

    if not text:
        return Response(content=b"", media_type="audio/pcm", status_code=400)

    gen = stream_pcm(text, voice, emotion)
    if fmt == "pcm":
        return StreamingResponse(gen, media_type="audio/pcm")

    # WAV: materialize then wrap with a header.
    pcm = bytearray()
    async for chunk in gen:
        pcm.extend(chunk)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(bytes(pcm))
    total_ms = len(pcm) / 2 / SAMPLE_RATE * 1000
    logger.info(f"WAV: {total_ms:.0f}ms audio")
    return Response(content=buf.getvalue(), media_type="audio/wav")


@app.get("/health")
async def health():
    return {"status": "ok", "provider": "neutts-2e", "sample_rate": SAMPLE_RATE}


@app.get("/v1/models")
async def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "neutts-2e",
                "object": "model",
                "created": 0,
                "owned_by": "neuphonic",
            },
            {"id": "tts-1", "object": "model", "created": 0, "owned_by": "neuphonic"},
        ],
    }


@app.get("/")
async def root():
    return {
        "service": "neutts-bridge",
        "endpoints": ["/v1/audio/speech", "/v1/models", "/health"],
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8003)
