    """

    frequency_penalty: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=4096, ge=1)
    presence_penalty: float | None = Field(default=None, ge=0.0, le=2.0)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    top_k: int | None = Field(default=None, ge=0)
    top_p: float | None = Field(default=None, ge=0.0, le=1.0)
    modalities: GeminiModalities | None = Field(default=GeminiModalities.AUDIO)
    language: Language | None = Field(default=Language.EN_US)
    media_resolution: GeminiMediaResolution | None = Field(
        default=GeminiMediaResolution.UNSPECIFIED
    )
    vad: GeminiVADParams | None = Field(default=None)
    context_window_compression: ContextWindowCompressionParams | None = Field(default=None)
    thinking: ThinkingConfig | None = Field(default=None)
    enable_affective_dialog: bool | None = Field(default=None)
    proactivity: ProactivityConfig | None = Field(default=None)
    extra: dict[str, Any] | None = Field(default_factory=dict)


@dataclass
class GeminiLiveLLMSettings(LLMSettings):
    """Settings for GeminiLiveLLMService.

    Parameters:
        voice: TTS voice identifier (e.g. ``"Charon"``).
        modalities: Response modalities.
        language: Language for generation.
        media_resolution: Media resolution setting.
        vad: Voice activity detection parameters.
        context_window_compression: Context window compression configuration.
        thinking: Thinking configuration.
        enable_affective_dialog: Whether to enable affective dialog.
        proactivity: Proactivity configuration.
    """

    voice: str | _NotGiven = field(default_factory=lambda: NOT_GIVEN)
    modalities: GeminiModalities | _NotGiven = field(default_factory=lambda: NOT_GIVEN)
    language: Language | str | _NotGiven = field(default_factory=lambda: NOT_GIVEN)
    media_resolution: GeminiMediaResolution | _NotGiven = field(default_factory=lambda: NOT_GIVEN)
    vad: GeminiVADParams | None | _NotGiven = field(default_factory=lambda: NOT_GIVEN)
    context_window_compression: ContextWindowCompressionParams | dict | _NotGiven = field(
        default_factory=lambda: NOT_GIVEN
    )
    thinking: ThinkingConfig | dict | _NotGiven = field(default_factory=lambda: NOT_GIVEN)
    enable_affective_dialog: bool | _NotGiven = field(default_factory=lambda: NOT_GIVEN)
    proactivity: ProactivityConfig | dict | _NotGiven = field(default_factory=lambda: NOT_GIVEN)


class GeminiLiveLLMService(LLMService[GeminiLiveLLMAdapter]):
    """Provides access to Google's Gemini Live API.

    This service enables real-time conversations with Gemini, supporting both
    text and audio modalities. It handles voice transcription, streaming audio
    responses, and tool usage.

    Does NOT emit ``UserStartedSpeakingFrame`` / ``UserStoppedSpeakingFrame``
    (the API exposes an ``interrupted`` event but no turn-start/-end), so
    pipeline processors that depend on those frames â€” RTVI client speech
    events, ``TurnTrackingObserver``, ``AudioBufferProcessor`` turn
    recording, ``UserIdleController``, user mute strategies, voicemail
    detector â€” won't activate with the default server-VAD-only setup.
    ``LLMContextAggregatorPair`` auto-detects this realtime service so context
    writes are correct anyway. To produce the turn frames
    locally, see ``examples/realtime/realtime-gemini-live-locally-driven-turns.py``;
    note that locally-generated turn boundaries are a heuristic and may
    not match Gemini Live's server-side turn decisions.
    """

    Settings = GeminiLiveLLMSettings
    _settings: Settings

    # Overriding the default adapter to use the Gemini Live one.
    adapter_class = GeminiLiveLLMAdapter

    def service_metadata_frame(self) -> LLMServiceMetadataFrame:
        """Realtime service; emits no server-side turn frames, so recommends no external strategies."""
        # The API exposes an `interrupted` event but no turn-start/-end.
        self._warn_if_realtime_service_emits_no_turn_frames(emits_turn_frames=False)
        return LLMServiceMetadataFrame(service_name=self.name, is_realtime_service=True)

    @property
    def _is_gemini_3(self) -> bool:
        """Check if the current model is a Gemini 3.x model."""
        return "gemini-3" in (assert_given(self._settings.model) or "")

    @property
    def _supports_non_blocking_tools(self) -> bool:
        """Whether the current model supports the NON_BLOCKING tool behavior + scheduling hints.

        Gemini 3.x has not yet shipped support for NON_BLOCKING function
        declarations or for the ``scheduling`` field on FunctionResponse.
        """
        return not self._is_gemini_3

    def __init__(
        self,
        *,
        api_key: str,
        model: str | None = None,
        voice_id: str = "Charon",
        start_audio_paused: bool = False,
        start_video_paused: bool = False,
        system_instruction: str | None = None,
        tools: ToolsSchema | list[FunctionSchema | DirectFunction] | list[dict] | None = None,
        params: InputParams | None = None,
        settings: Settings | None = None,
        inference_on_context_initialization: bool = True,
        user_audio_preroll_secs: float | None = None,
        file_api_base_url: str = "https://generativelanguage.googleapis.com/v1beta/files",
        http_options: HttpOptions | None = None,
        **kwargs,
    ):
        """Initialize the Gemini Live LLM service.

        Args:
            api_key: Google AI API key for authentication.
            model: Model identifier to use.

                .. deprecated:: 0.0.105
                    Use ``settings=GeminiLiveLLMService.Settings(model=...)`` instead.
                    Will be removed in 2.0.0.

            voice_id: TTS voice identifier. Defaults to "Charon".

                .. deprecated:: 0.0.105
                    Use ``settings=GeminiLiveLLMService.Settings(voice=...)`` instead.
                    Will be removed in 2.0.0.

            start_audio_paused: Whether to start with audio input paused. Defaults to False.
            start_video_paused: Whether to start with video input paused. Defaults to False.
            system_instruction: System prompt for the model. Defaults to None.
            tools: Tools available to the model: a ``ToolsSchema``, a plain list of
                direct functions and/or ``FunctionSchema`` objects (handlers
                auto-register), or a list of provider-native tool dicts. Defaults
                to None.
            params: Configuration parameters for the model.

                .. deprecated:: 0.0.105
                    Use ``settings=GeminiLiveLLMService.Settings(...)`` instead.
                    Will be removed in 2.0.0.

            settings: Gemini Live LLM settings. If provided together with deprecated
                top-level parameters, the ``settings`` values take precedence.
            inference_on_context_initialization: Whether to generate a response when context
                is first set. Defaults to True.
            user_audio_preroll_secs: In server-VAD-disabled (locally-driven
                turns) mode, how much recent audio to replay after
                activity_start so the speech onset isn't clipped. Defaults to

