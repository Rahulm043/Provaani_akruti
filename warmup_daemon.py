#!/usr/bin/env python3
"""
Provaani Production Warmup & Heartbeat Daemon
Runs every 10 minutes to keep all external AI providers, TLS sessions,
DNS caches, and database connection pools 100% warm 24/7/365.
"""
import asyncio
import time
import httpx
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

CEREBRAS_API_KEY = "csk-wcpmyy58frvy386y8wjkxv39p2wmne6rkpv284hvfcwktnfj"
SMALLEST_API_KEY = "sk_d341cbfa5e2ad090db0691e1482590d6"

async def warm_internal_api(client: httpx.AsyncClient):
    try:
        t0 = time.time()
        resp = await client.get("http://127.0.0.1:8000/api/v1/health", timeout=5.0)
        logging.info(f"[Warmup] Internal API: {resp.status_code} in {time.time()-t0:.3f}s")
    except Exception as e:
        logging.warning(f"[Warmup] Internal API error: {e}")

async def warm_cerebras_llm(client: httpx.AsyncClient):
    try:
        t0 = time.time()
        resp = await client.post(
            "https://api.cerebras.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "gpt-oss-120b",
                "messages": [{"role": "user", "content": "ping"}],
                "max_tokens": 2
            },
            timeout=8.0
        )
        logging.info(f"[Warmup] Cerebras LLM: {resp.status_code} in {time.time()-t0:.3f}s")
    except Exception as e:
        logging.warning(f"[Warmup] Cerebras error: {e}")

async def warm_smallest_tts(client: httpx.AsyncClient):
    try:
        t0 = time.time()
        resp = await client.post(
            "https://api.smallest.ai/waves/v1/tts",
            headers={"Authorization": f"Bearer {SMALLEST_API_KEY}", "Content-Type": "application/json"},
            json={"text": "hi", "voice_id": "meher", "speed": 1.0},
            timeout=8.0
        )
        logging.info(f"[Warmup] Smallest TTS: {resp.status_code} in {time.time()-t0:.3f}s")
    except Exception as e:
        logging.warning(f"[Warmup] Smallest TTS error: {e}")

async def run_warmup():
    async with httpx.AsyncClient() as client:
        await asyncio.gather(
            warm_internal_api(client),
            warm_cerebras_llm(client),
            warm_smallest_tts(client),
            return_exceptions=True
        )

if __name__ == "__main__":
    asyncio.run(run_warmup())
