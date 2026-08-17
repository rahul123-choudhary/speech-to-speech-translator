"""Declared direct-S2ST output languages and their deployment metadata."""

from typing import Literal


TargetLanguage = Literal["es", "en", "hi", "fr", "pt"]

TARGET_LANGUAGES: dict[str, dict[str, str]] = {
    "es": {"name": "Spanish", "asr_language": "es"},
    "en": {"name": "English", "asr_language": "en"},
    "hi": {"name": "Hindi", "asr_language": "hi"},
    "fr": {"name": "French", "asr_language": "fr"},
    "pt": {"name": "Portuguese", "asr_language": "pt"},
}
