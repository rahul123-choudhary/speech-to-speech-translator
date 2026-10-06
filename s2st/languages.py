"""Declared direct-S2ST oral-tradition source and target output languages, metadata, and benchmarks."""

from typing import Any, Literal

# Primary source language: Yorùbá, paired with English in the IWSLT 2026 S2S data.
SOURCE_LANGUAGE = "yo"

SOURCE_LANGUAGES: dict[str, dict[str, Any]] = {
    "yo": {
        "code": "yo",
        "name": "Yorùbá",
        "native_name": "Yorùbá",
        "family": "Niger-Congo",
        "region": "Nigeria and neighboring West Africa",
        "tradition": "Yorùbá language with a rich oral heritage",
        "iso_639_3": "yor",
        "resource_level": "Low-resource speech translation; IWSLT 2026 provides aligned Yoruba and English speech",
        "primary_targets": ["en"],
    },
}

SOURCE_LANGUAGE_INFO = SOURCE_LANGUAGES[SOURCE_LANGUAGE]

# No literature score is recorded until its primary citation can be verified.
LITERATURE_BENCHMARKS: dict[str, dict[str, Any]] = {}

TargetLanguage = Literal[
    "or", "te", "hi", "en", "bn", "ta", "kn", "mr", "gu", "ml", "pa", "es",
    "as", "ur", "ne", "ar", "zh", "fr", "de", "pt", "ru", "ja", "ko", "id", "tr", "vi", "it",
]

TARGET_LANGUAGES: dict[str, dict[str, Any]] = {
    "or": {
        "name": "Odia",
        "native_name": "ଓଡ଼ିଆ",
        "state": "Odisha",
        "asr_language": "or",
        "default_voice": "or-IN-SukantNeural",
        "available_voices": ["or-IN-SukantNeural", "or-IN-LaxmipriyaNeural", "or-IN-Standard-Male"],
    },
    "te": {
        "name": "Telugu",
        "native_name": "తెలుగు",
        "state": "Andhra Pradesh / Telangana",
        "asr_language": "te",
        "default_voice": "te-IN-MohanNeural",
        "available_voices": ["te-IN-MohanNeural", "te-IN-ShrutiNeural", "te-IN-Standard-Female"],
    },
    "hi": {
        "name": "Hindi",
        "native_name": "हिन्दी",
        "state": "Central / Northern India",
        "asr_language": "hi",
        "default_voice": "hi-IN-MadhurNeural",
        "available_voices": ["hi-IN-MadhurNeural", "hi-IN-SwaraNeural"],
    },
    "en": {
        "name": "English",
        "native_name": "English",
        "state": "Primary IWSLT 2026 target",
        "asr_language": "en",
        "default_voice": "en-IN-PrabhatNeural",
        "available_voices": ["en-IN-PrabhatNeural", "en-IN-NeerjaNeural"],
    },
    "bn": {
        "name": "Bengali",
        "native_name": "বাংলা",
        "state": "West Bengal / Tripura",
        "asr_language": "bn",
        "default_voice": "bn-IN-BashkarNeural",
        "available_voices": ["bn-IN-BashkarNeural", "bn-IN-TanishaaNeural"],
    },
    "ta": {
        "name": "Tamil",
        "native_name": "தமிழ்",
        "state": "Tamil Nadu / Puducherry",
        "asr_language": "ta",
        "default_voice": "ta-IN-ValluvarNeural",
        "available_voices": ["ta-IN-ValluvarNeural", "ta-IN-PallaviNeural"],
    },
    "kn": {
        "name": "Kannada",
        "native_name": "ಕನ್ನಡ",
        "state": "Karnataka",
        "asr_language": "kn",
        "default_voice": "kn-IN-GaganNeural",
        "available_voices": ["kn-IN-GaganNeural", "kn-IN-SapnaNeural"],
    },
    "mr": {
        "name": "Marathi",
        "native_name": "मराठी",
        "state": "Maharashtra",
        "asr_language": "mr",
        "default_voice": "mr-IN-ManoharNeural",
        "available_voices": ["mr-IN-ManoharNeural", "mr-IN-AarohiNeural"],
    },
    "gu": {
        "name": "Gujarati",
        "native_name": "ગુજરાતી",
        "state": "Gujarat",
        "asr_language": "gu",
        "default_voice": "gu-IN-NiranjanNeural",
        "available_voices": ["gu-IN-NiranjanNeural", "gu-IN-DhwaniNeural"],
    },
    "ml": {
        "name": "Malayalam",
        "native_name": "മലയാളം",
        "state": "Kerala",
        "asr_language": "ml",
        "default_voice": "ml-IN-MidhunNeural",
        "available_voices": ["ml-IN-MidhunNeural", "ml-IN-SobhanaNeural"],
    },
    "pa": {
        "name": "Punjabi",
        "native_name": "ਪੰਜਾਬੀ",
        "state": "Punjab",
        "asr_language": "pa",
        "default_voice": "pa-IN-HarjitNeural",
        "available_voices": ["pa-IN-HarjitNeural", "pa-IN-GurpreetNeural"],
    },
    "es": {
        "name": "Spanish",
        "native_name": "Español",
        "state": "International",
        "asr_language": "es",
        "default_voice": "es-ES-AlvaroNeural",
        "available_voices": ["es-ES-AlvaroNeural", "es-ES-ElviraNeural"],
    },
}

# Additional selectable output languages. The active corpus-backed research pair
# is Yorùbá to English; other targets need their own aligned data and checkpoints.
_ADDITIONAL_TARGETS = {
    "as": ("Assamese", "অসমীয়া", "Assam", "as-IN-PriyomNeural"),
    "ur": ("Urdu", "اردو", "India / Pakistan", "ur-IN-GulNeural"),
    "ne": ("Nepali", "नेपाली", "India / Nepal", "ne-NP-HemkalaNeural"),
    "ar": ("Arabic", "العربية", "International", "ar-SA-HamedNeural"),
    "zh": ("Chinese (Mandarin)", "中文", "International", "zh-CN-YunfengNeural"),
    "fr": ("French", "Français", "International", "fr-FR-HenriNeural"),
    "de": ("German", "Deutsch", "International", "de-DE-ConradNeural"),
    "pt": ("Portuguese", "Português", "International", "pt-BR-NicolauNeural"),
    "ru": ("Russian", "Русский", "International", "ru-RU-DmitryNeural"),
    "ja": ("Japanese", "日本語", "International", "ja-JP-KeitaNeural"),
    "ko": ("Korean", "한국어", "International", "ko-KR-InJoonNeural"),
    "id": ("Indonesian", "Bahasa Indonesia", "International", "id-ID-ArdiNeural"),
    "tr": ("Turkish", "Türkçe", "International", "tr-TR-AhmetNeural"),
    "vi": ("Vietnamese", "Tiếng Việt", "International", "vi-VN-NamMinhNeural"),
    "it": ("Italian", "Italiano", "International", "it-IT-DiegoNeural"),
}
for _code, (_name, _native_name, _region, _voice) in _ADDITIONAL_TARGETS.items():
    TARGET_LANGUAGES[_code] = {
        "name": _name,
        "native_name": _native_name,
        "state": _region,
        "asr_language": _code,
        "default_voice": _voice,
        "available_voices": [_voice],
        "translation_checkpoint_required": True,
    }
