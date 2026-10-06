from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    firebase_credentials_path: Path | None = None
    firebase_project_id: str | None = None
    firebase_api_key: str | None = None
    firebase_auth_domain: str | None = None
    firebase_app_id: str | None = None
    firebase_storage_bucket: str | None = None
    firebase_measurement_id: str | None = None
    allow_development_auth: bool = False
    mongodb_uri: str | None = None
    mongodb_database: str = "yoruba_s2st"
    encoder_model: str = "facebook/wav2vec2-xls-r-300m"
    asr_model: str = "openai/whisper-small"
    device: str = "cpu"
    max_utterance_seconds: int = 15
    # Target language checkpoints
    s2st_checkpoint_or: Path | None = None
    s2st_checkpoint_te: Path | None = None
    s2st_checkpoint_hi: Path | None = None
    s2st_checkpoint_en: Path | None = None
    s2st_checkpoint_bn: Path | None = None
    s2st_checkpoint_ta: Path | None = None
    s2st_checkpoint_kn: Path | None = None
    s2st_checkpoint_mr: Path | None = None
    s2st_checkpoint_gu: Path | None = None
    s2st_checkpoint_ml: Path | None = None
    s2st_checkpoint_pa: Path | None = None
    s2st_checkpoint_es: Path | None = None
    s2st_checkpoint_quz: Path | None = None
    s2st_checkpoint_as: Path | None = None
    s2st_checkpoint_ur: Path | None = None
    s2st_checkpoint_ne: Path | None = None
    s2st_checkpoint_ar: Path | None = None
    s2st_checkpoint_zh: Path | None = None
    s2st_checkpoint_fr: Path | None = None
    s2st_checkpoint_de: Path | None = None
    s2st_checkpoint_pt: Path | None = None
    s2st_checkpoint_ru: Path | None = None
    s2st_checkpoint_ja: Path | None = None
    s2st_checkpoint_ko: Path | None = None
    s2st_checkpoint_id: Path | None = None
    s2st_checkpoint_tr: Path | None = None
    s2st_checkpoint_vi: Path | None = None
    s2st_checkpoint_it: Path | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
