

def _audio_token_count(details: list[ModalityTokenCount] | None) -> int | None:
    """Get the AUDIO token count from a modality breakdown, if reported.

    Gemini omits modalities with no tokens (and omits the list entirely when
    there is no breakdown), so absence means "not reported" rather than zero.

    Args:
        details: A modality breakdown from usage metadata, e.g.
            ``prompt_tokens_details``.

    Returns:
        The AUDIO token count, or ``None`` if not reported.
    """
    if not details:
        return None
    for entry in details:
        if entry.modality == MediaModality.AUDIO:
            return entry.token_count
    return None


# Pre-roll cushion added on top of the auto-sized duration (start_secs), to
# absorb small timing slop between start_secs and the audio actually clipped,
# and to give a bit of extra audio context for the model.
# Not applied to an explicit user_audio_preroll_secs override.
AUTOSIZED_USER_AUDIO_PREROLL_MARGIN_SECS = 0.1
# Pre-roll used before start_secs is known (no SpeechControlParamsFrame yet, or
# no upstream VAD) and no override is given.
DEFAULT_USER_AUDIO_PREROLL_SECS = 0.5


def language_to_gemini_language(language: Language) -> str:
    """Maps a Language enum value to a Gemini Live supported language code.

    Source:
    https://ai.google.dev/api/generate-content#MediaResolution

    Args:
        language: The language enum value to convert.

    Returns:
        The Gemini language code string. If ``language`` is not in the
        verified mapping, falls back to the full language code string and logs
        a warning (via ``resolve_language(..., use_base_code=False)``).
    """
    LANGUAGE_MAP = {
        # Arabic
        Language.AR: "ar-XA",
        # Bengali
        Language.BN_IN: "bn-IN",
        # Chinese (Mandarin)
        Language.CMN: "cmn-CN",
        Language.CMN_CN: "cmn-CN",
        Language.ZH: "cmn-CN",  # Map general Chinese to Mandarin for Gemini
        Language.ZH_CN: "cmn-CN",  # Map Simplified Chinese to Mandarin for Gemini
        # German
        Language.DE: "de-DE",
        Language.DE_DE: "de-DE",
        # English
        Language.EN: "en-US",  # Default to US English (though not explicitly listed in supported codes)
        Language.EN_US: "en-US",
        Language.EN_AU: "en-AU",
        Language.EN_GB: "en-GB",
        Language.EN_IN: "en-IN",
        # Spanish
        Language.ES: "es-ES",  # Default to Spain Spanish
        Language.ES_ES: "es-ES",
        Language.ES_US: "es-US",
        # French
        Language.FR: "fr-FR",  # Default to France French
        Language.FR_FR: "fr-FR",
        Language.FR_CA: "fr-CA",
        # Gujarati
        Language.GU: "gu-IN",
        Language.GU_IN: "gu-IN",
        # Hindi
        Language.HI: "hi-IN",
        Language.HI_IN: "hi-IN",
        # Indonesian
        Language.ID: "id-ID",
        Language.ID_ID: "id-ID",
        # Italian
        Language.IT: "it-IT",
        Language.IT_IT: "it-IT",
        # Japanese
        Language.JA: "ja-JP",
        Language.JA_JP: "ja-JP",
        # Kannada
        Language.KN: "kn-IN",
        Language.KN_IN: "kn-IN",
        # Korean
        Language.KO: "ko-KR",
        Language.KO_KR: "ko-KR",
        # Malayalam
        Language.ML: "ml-IN",
        Language.ML_IN: "ml-IN",
        # Marathi
        Language.MR: "mr-IN",
        Language.MR_IN: "mr-IN",
        # Dutch
        Language.NL: "nl-NL",
        Language.NL_NL: "nl-NL",
        # Polish
        Language.PL: "pl-PL",
        Language.PL_PL: "pl-PL",
        # Portuguese (Brazil)
        Language.PT_BR: "pt-BR",
        # Russian
        Language.RU: "ru-RU",
        Language.RU_RU: "ru-RU",
        # Tamil
        Language.TA: "ta-IN",
        Language.TA_IN: "ta-IN",
        # Telugu
        Language.TE: "te-IN",
        Language.TE_IN: "te-IN",
        # Thai
        Language.TH: "th-TH",
        Language.TH_TH: "th-TH",
        # Turkish
        Language.TR: "tr-TR",
        Language.TR_TR: "tr-TR",
        # Vietnamese
        Language.VI: "vi-VN",
        Language.VI_VN: "vi-VN",
    }

    return resolve_language(language, LANGUAGE_MAP, use_base_code=False)

