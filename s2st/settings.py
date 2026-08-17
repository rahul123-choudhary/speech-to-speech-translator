from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    firebase_credentials_path: Path | None = None
    firebase_project_id: str | None = None
    mongodb_uri: str | None = None
    mongodb_database: str = "quechua_s2st"
    encoder_model: str = "facebook/wav2vec2-xls-r-300m"
    asr_model: str = "openai/whisper-small"
    device: str = "cuda"
    max_utterance_seconds: int = 15
    s2st_checkpoint_es: Path | None = None
    s2st_checkpoint_en: Path | None = None
    s2st_checkpoint_hi: Path | None = None
    s2st_checkpoint_fr: Path | None = None
    s2st_checkpoint_pt: Path | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
