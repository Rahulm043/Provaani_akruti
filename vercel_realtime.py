"""Dograh Vercel AI Gateway Realtime LLM Service for Gemini 3.8 Live.

Connects to Vercel AI Gateway (wss://ai-gateway.vercel.sh/v4/ai/realtime-model?ai-model-id=google%2Fgemini-3.8-live)
using ephemeral client-secret tokens minted via https://ai-gateway.vercel.sh/v1/realtime/client-secrets.
Translates Pipecat frames to/from the normalized Vercel AI Gateway Realtime protocol.
"""

import asyncio
import base64
import json
import uuid
from typing import Any

from loguru import logger
import requests
import websockets

from pipecat.audio.utils import create_stream_resampler
from api.services.pipecat.realtime.static_greeting import format_static_greeting_prompt
from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    CancelFrame,
    EndFrame,
    Frame,
    InputAudioRawFrame,
    LLMContextFrame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    LLMMessagesAppendFrame,
    LLMSetToolsFrame,
    StartFrame,
    TranscriptionFrame,
    TTSAudioRawFrame,
    TTSSpeakFrame,
    TTSStartedFrame,
    TTSStoppedFrame,
    UserMuteStartedFrame,
    UserMuteStoppedFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
    VADUserStartedSpeakingFrame,
    VADUserStoppedSpeakingFrame,
)
from dataclasses import dataclass, field
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.llm_service import FunctionCallFromLLM, LLMService
from pipecat.services.settings import NOT_GIVEN, LLMSettings, _NotGiven
from pipecat.utils.time import time_now_iso8601


@dataclass
class VercelRealtimeLLMSettings(LLMSettings):
    voice: str | _NotGiven = field(default_factory=lambda: NOT_GIVEN)
    language: str | _NotGiven = field(default_factory=lambda: NOT_GIVEN)


class DograhVercelRealtimeLLMService(LLMService):
    """Dograh Realtime LLM service backed by Vercel AI Gateway."""

    Settings = VercelRealtimeLLMSettings

    def __init__(
        self,
        *,
        api_key: str,
        settings: VercelRealtimeLLMSettings | LLMSettings | None = None,
        model: str = "google/gemini-3.8-live",
        voice: str = "Aoede",
        language: str = "bn",
        system_instruction: str = "",
        **kwargs,
    ):
        if settings is None:
            settings = VercelRealtimeLLMSettings(
                model=model,
                voice=voice,
                language=language,
                system_instruction=system_instruction,
            )
        super().__init__(settings=settings, **kwargs)

        self._api_key = api_key
        self._model = getattr(settings, "model", None) or model
        self._voice = getattr(settings, "voice", None) or voice or "Aoede"
        if isinstance(self._voice, _NotGiven):
            self._voice = voice or "Aoede"
        self._language = getattr(settings, "language", None) or language or "bn"
        if isinstance(self._language, _NotGiven):
            self._language = language or "bn"
        self._system_instruction = getattr(settings, "system_instruction", None) or system_instruction or ""
        if isinstance(self._system_instruction, _NotGiven):
            self._system_instruction = system_instruction or ""

        self._ws = None
        self._connected = False
        self._disconnecting = False
        self._session_ready = asyncio.Event()
        self._receive_task: asyncio.Task | None = None
        self._user_is_muted: bool = False
        self._bot_is_speaking: bool = False
        self._handled_initial_context: bool = False
        self._context: LLMContext | None = None
        self._pending_initial_greeting: str | None = None
        self._input_resampler = create_stream_resampler()
        self._completed_tool_calls: set[str] = set()
        self._call_id_to_function_name: dict[str, str] = {}
        self._formatted_tools: list[dict[str, Any]] = []
        self._tools_ready: asyncio.Event = asyncio.Event()
        self._vad_commit_task: asyncio.Task | None = None
        self._user_has_spoken: bool = False

    @property
    def model_name(self) -> str:
        return self._model

    def _mint_token(self) -> str:
        url = "https://ai-gateway.vercel.sh/v1/realtime/client-secrets"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model,
            "providerOptions": {
                "google": {
                    "contextWindowCompression": {
                        "slidingWindow": {}
                    }
                }
            }
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()["token"]

    async def start(self, frame: StartFrame):
        await super().start(frame)
        self.create_task(self._connect())

    async def stop(self, frame: EndFrame):
        await super().stop(frame)
        await self._disconnect()

    async def cancel(self, frame: CancelFrame):
        await super().cancel(frame)
        await self._disconnect()

    async def _connect(self):
        if self._connected or self._disconnecting:
            return
        try:
            # Wait briefly for tools configuration from pipeline before connecting
            if not self._formatted_tools:
                try:
                    await asyncio.wait_for(self._tools_ready.wait(), timeout=0.6)
                except asyncio.TimeoutError:
                    pass

            token = await asyncio.to_thread(self._mint_token)
            ws_url = f"wss://ai-gateway.vercel.sh/v4/ai/realtime-model?ai-model-id={self._model.replace('/', '%2F')}"
            subprotocols = ["ai-gateway-realtime.v1", f"ai-gateway-auth.{token}"]
            logger.info(f"{self}: Connecting to Vercel AI Gateway ({self._model}) with {len(self._formatted_tools)} tools: {[t.get('name') for t in self._formatted_tools]}...")

            self._ws = await websockets.connect(ws_url, subprotocols=subprotocols)
            self._connected = True
            logger.info(f"{self}: Connected to Vercel AI Gateway WebSocket successfully!")

            self._receive_task = self.create_task(self._receive_loop())

            # Configure session with tools in initial update
            await self._send_session_update()

            # Wait for session-created confirmation
            try:
                await asyncio.wait_for(self._session_ready.wait(), timeout=6.0)
            except asyncio.TimeoutError:
                logger.warning(f"{self}: Timeout waiting for session-created from Vercel AI Gateway")

            if self._pending_initial_greeting:
                greeting = self._pending_initial_greeting
                self._pending_initial_greeting = None
                await self._trigger_greeting(greeting)
            elif not self._handled_initial_context:
                self._handled_initial_context = True
                await self._trigger_greeting("Call connected. Please deliver the opening greeting to the caller now.")
        except Exception as e:
            logger.error(f"{self}: Failed to connect to Vercel AI Gateway: {e}")
            await self.push_error(error_msg=f"Vercel AI Gateway connection error: {e}", exception=e)

    async def _send_session_update(self):
        if not self._ws or not self._connected:
            return
        session_config: dict[str, Any] = {
            "outputModalities": ["audio"],
            "instructions": self._system_instruction,
            "voice": self._voice,
        }
        if self._formatted_tools:
            session_config["tools"] = self._formatted_tools
        session_event = {
            "type": "session-update",
            "config": session_config,
        }
        await self._send_event(session_event)
        logger.debug(f"{self}: Sent session-update to Vercel Gateway (tools={len(self._formatted_tools)})")

    async def _disconnect(self):
        self._disconnecting = True
        self._connected = False
        self._session_ready.clear()
        if self._receive_task:
            self._receive_task.cancel()
            self._receive_task = None
        if self._vad_commit_task and not self._vad_commit_task.done():
            self._vad_commit_task.cancel()
            self._vad_commit_task = None
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        self._ws = None

    async def _update_settings(self, delta: LLMSettings) -> dict[str, Any]:
        changed = await super()._update_settings(delta)
        if "system_instruction" in changed:
            self._system_instruction = self._settings.system_instruction or ""
            await self._send_session_update()
        if "voice" in changed:
            self._voice = getattr(self._settings, "voice", "Aoede")
            await self._send_session_update()
        return changed

    async def process_frame(self, frame: Frame, direction: FrameDirection = FrameDirection.DOWNSTREAM):
        if not isinstance(frame, InputAudioRawFrame):
            logger.info(f"{self}: process_frame received {type(frame).__name__}")

        if isinstance(frame, StartFrame):
            await super().process_frame(frame, direction)
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, UserMuteStartedFrame):
            self._user_is_muted = True
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, UserMuteStoppedFrame):
            self._user_is_muted = False
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, (UserStartedSpeakingFrame, VADUserStartedSpeakingFrame)):
            self._user_has_spoken = True
            if self._vad_commit_task and not self._vad_commit_task.done():
                self._vad_commit_task.cancel()
                self._vad_commit_task = None
            if isinstance(frame, UserStartedSpeakingFrame) and self._bot_is_speaking:
                logger.info(f"{self}: User interruption detected, cancelling active response")
                await self._send_event({"type": "response-cancel"})
                self._bot_is_speaking = False
                await self.push_frame(TTSStoppedFrame())
                await self.push_frame(BotStoppedSpeakingFrame())
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, VADUserStoppedSpeakingFrame):
            # Fast VAD speech stop debounce (600ms)
            if self._user_has_spoken and self._connected and not self._user_is_muted:
                if self._vad_commit_task and not self._vad_commit_task.done():
                    self._vad_commit_task.cancel()
                self._vad_commit_task = self.create_task(self._delayed_turn_commit(delay=0.6))
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, UserStoppedSpeakingFrame):
            # Fallback or explicit turn-stopped aggregator frame
            if self._vad_commit_task and not self._vad_commit_task.done():
                self._vad_commit_task.cancel()
                self._vad_commit_task = None
            await self._commit_turn()
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, TTSSpeakFrame):
            greeting_text = frame.text.strip() if frame.text else ""
            if not self._handled_initial_context and greeting_text:
                self._handled_initial_context = True
                if self._connected and self._session_ready.is_set():
                    await self._trigger_greeting(greeting_text)
                else:
                    self._pending_initial_greeting = greeting_text
            # Consume TTSSpeakFrame without forwarding to TTS since Gemini generates its own audio
            return

        if isinstance(frame, LLMSetToolsFrame):
            self._update_tools_from_frame(frame)
            self._tools_ready.set()
            logger.info(f"{self}: Processed LLMSetToolsFrame: {len(self._formatted_tools)} tools ready: {[t.get('name') for t in self._formatted_tools]}")
            if self._connected and not self._session_ready.is_set():
                await self._send_session_update()
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, LLMContextFrame):
            self._context = frame.context
            if not self._handled_initial_context:
                self._handled_initial_context = True
                prompt_to_say = self._pending_initial_greeting or "Call connected. Please deliver the opening greeting to the caller now."
                self._pending_initial_greeting = None
                if self._connected and self._session_ready.is_set():
                    await self._trigger_greeting(prompt_to_say)
                else:
                    self._pending_initial_greeting = prompt_to_say
            else:
                await self._process_completed_function_calls()
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, InputAudioRawFrame):
            if not self._user_is_muted and self._connected:
                await self._send_user_audio(frame)
            await self.push_frame(frame, direction)
            return

        await super().process_frame(frame, direction)
        await self.push_frame(frame, direction)

    def _update_tools_from_frame(self, frame: LLMSetToolsFrame):
        formatted: list[dict[str, Any]] = []
        seen = set()
        tools_schema = frame.tools_schema
        if hasattr(tools_schema, "standard_tools") and tools_schema.standard_tools:
            for tool in tools_schema.standard_tools:
                t_dict = tool.to_default_dict()
                name = t_dict.get("name")
                if not name or name in seen:
                    continue
                seen.add(name)
                formatted.append({
                    "type": "function",
                    "name": name,
                    "description": t_dict.get("description", ""),
                    "parameters": t_dict.get("parameters", {"type": "object", "properties": {}}),
                })
        self._formatted_tools = formatted

    async def _send_event(self, event: dict):
        if not self._ws or not self._connected:
            return
        if event.get("type") == "input-audio-append" and not event.get("audio"):
            return
        try:
            await self._ws.send(json.dumps(event))
        except Exception as e:
            logger.warning(f"{self}: Error sending event ({event.get('type')}) to Vercel Gateway: {e}")

    async def _send_user_audio(self, frame: InputAudioRawFrame):
        if not self._connected or not self._ws:
            return
        pcm_data = frame.audio
        if not pcm_data:
            return
        if frame.sample_rate != 16000 and hasattr(self, "_input_resampler"):
            pcm_data = await self._input_resampler.resample(pcm_data, frame.sample_rate, 16000)

        if not pcm_data:
            return

        b64_audio = base64.b64encode(pcm_data).decode("ascii")
        if not b64_audio:
            return

        event = {
            "type": "input-audio-append",
            "audio": b64_audio,
        }
        await self._send_event(event)

    async def _delayed_turn_commit(self, delay: float = 0.6):
        try:
            await asyncio.sleep(delay)
            if self._user_has_spoken and self._connected and not self._user_is_muted:
                logger.info(f"{self}: VAD silence debounce ({delay}s) elapsed. Fast-committing user turn to Gemini.")
                await self._commit_turn()
        except asyncio.CancelledError:
            pass

    async def _commit_turn(self):
        if not self._user_has_spoken or not self._connected or self._user_is_muted:
            return
        self._user_has_spoken = False
        silence_16k = b"\x00" * 3200  # 100ms silence at 16kHz to cleanly trigger server VAD activity end
        await self._send_event({
            "type": "input-audio-append",
            "audio": base64.b64encode(silence_16k).decode("ascii"),
        })
        await self._send_event({"type": "input-audio-commit"})
        logger.info(f"{self}: Committed user audio turn to Vercel Gateway")

    async def _trigger_greeting(self, text: str):
        if not self._session_ready.is_set():
            logger.info(f"{self}: Waiting for session-created before triggering greeting...")
            try:
                await asyncio.wait_for(self._session_ready.wait(), timeout=6.0)
            except asyncio.TimeoutError:
                logger.warning(f"{self}: Timeout waiting for session-created before greeting")

        logger.info(f"{self}: Triggering initial greeting turn: {text[:60]}...")
        if text.startswith("Call connected"):
            prompt = text
        else:
            prompt = format_static_greeting_prompt(text)
        msg_event = {
            "type": "conversation-item-create",
            "item": {
                "type": "text-message",
                "role": "user",
                "text": prompt,
            },
        }
        # In Gemini Live, conversation-item-create automatically triggers model generation.
        # DO NOT send response-create (triggers 1008 rejection).
        await self._send_event(msg_event)

    async def _process_completed_function_calls(self):
        if not self._context:
            return
        for msg in self._context.get_messages():
            if not isinstance(msg, dict):
                continue
            if msg.get("role") == "tool" and msg.get("content") != "IN_PROGRESS":
                tool_call_id = msg.get("tool_call_id")
                if tool_call_id and tool_call_id not in self._completed_tool_calls:
                    content = msg.get("content", "")
                    if not isinstance(content, str):
                        content = json.dumps(content)
                    func_name = self._call_id_to_function_name.get(tool_call_id)
                    output_item: dict[str, Any] = {
                        "type": "function-call-output",
                        "callId": tool_call_id,
                        "output": content,
                    }
                    if func_name:
                        output_item["name"] = func_name
                    logger.debug(f"{self}: Sending function call result for {tool_call_id} ({func_name})")
                    await self._send_event({
                        "type": "conversation-item-create",
                        "item": output_item,
                    })
                    self._completed_tool_calls.add(tool_call_id)

    async def _receive_loop(self):
        logger.debug(f"{self}: Starting Vercel AI Gateway receive loop")
        try:
            while self._connected and self._ws:
                msg = await self._ws.recv()
                event = json.loads(msg)
                ev_type = event.get("type")

                if ev_type == "session-created":
                    logger.info(f"{self}: Session established with Vercel AI Gateway!")
                    self._session_ready.set()
                elif ev_type == "audio-delta":
                    delta_b64 = event.get("delta", "")
                    if delta_b64:
                        pcm_bytes = base64.b64decode(delta_b64)
                        if not self._bot_is_speaking:
                            self._bot_is_speaking = True
                            await self.push_frame(BotStartedSpeakingFrame())
                            await self.push_frame(TTSStartedFrame())
                            await self.push_frame(LLMFullResponseStartFrame())
                        await self.push_frame(
                            TTSAudioRawFrame(
                                audio=pcm_bytes,
                                sample_rate=24000,
                                num_channels=1,
                            )
                        )
                elif ev_type == "audio-transcript-delta":
                    delta_text = event.get("delta", "")
                    if delta_text:
                        await self.push_frame(
                            TranscriptionFrame(
                                text=delta_text,
                                user_id="assistant",
                                timestamp=time_now_iso8601(),
                            )
                        )
                elif ev_type in ("audio-done", "response-done") or (ev_type == "custom" and event.get("rawType") == "generationComplete"):
                    if self._bot_is_speaking:
                        self._bot_is_speaking = False
                        await self.push_frame(TTSStoppedFrame())
                        await self.push_frame(LLMFullResponseEndFrame())
                        await self.push_frame(BotStoppedSpeakingFrame())

                    raw = event.get("raw", {})
                    usage = raw.get("usageMetadata")
                    if usage:
                        prompt_tokens = usage.get("promptTokenCount", 0)
                        completion_tokens = usage.get("responseTokenCount", 0)
                        total_tokens = usage.get("totalTokenCount", 0)
                        logger.info(
                            f"{self}: Vercel response done. Tokens: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}"
                        )
                elif ev_type == "input-transcription-completed":
                    user_transcript = event.get("transcript", "")
                    if user_transcript:
                        logger.info(f"{self}: User speech transcribed by Gemini: '{user_transcript}'")
                        await self.push_frame(
                            TranscriptionFrame(
                                text=user_transcript,
                                user_id="user",
                                timestamp=time_now_iso8601(),
                            )
                        )
                elif ev_type == "function-call-arguments-done":
                    call_id = event.get("callId", str(uuid.uuid4()))
                    name = event.get("name", "")
                    raw_args = event.get("arguments", "{}")
                    logger.info(f"{self}: Function call received from Gemini: {name} (id={call_id})")
                    try:
                        args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                    except Exception:
                        args = {}

                    self._call_id_to_function_name[call_id] = name
                    function_call = FunctionCallFromLLM(
                        function_name=name,
                        tool_call_id=call_id,
                        arguments=args,
                    )
                    await self.run_function_calls([function_call])
        except asyncio.CancelledError:
            pass
        except Exception as e:
            if self._connected:
                logger.error(f"{self}: Error in Vercel AI Gateway receive loop: {e}")
                await self.push_error(error_msg=f"Vercel AI Gateway receive error: {e}", exception=e)
