import json
from pathlib import Path
from typing import Iterator

from pydantic import BaseModel, Field


class Utterance(BaseModel):
    id: str
    source_audio: str
    target_audio: str | None = None
    reference_translation: str
    source_transcript: str | None = None
    speaker_id: str | None = None
    split: str | None = None
    provenance: str
    target_speech_generator: str | None = None
    consent_id: str | None = None
    extra: dict = Field(default_factory=dict)


def read_manifest(path: str | Path) -> Iterator[Utterance]:
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if line.strip():
                try:
                    yield Utterance.model_validate_json(line)
                except ValueError as error:
                    raise ValueError(f"Invalid record at {path}:{line_number}") from error


def write_manifest(records: list[Utterance], path: str | Path) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record.model_dump(), ensure_ascii=False) + "\n")

