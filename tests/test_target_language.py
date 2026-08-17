from pathlib import Path

import pytest

from s2st.manifest import Utterance
from s2st.target_language import (
    make_target_candidates,
    read_approved_references,
    validate_target_language,
    write_reference_template,
)


def test_target_language_templates_require_human_approval(tmp_path: Path) -> None:
    source = tmp_path / "clip.wav"
    source.write_bytes(b"source")
    record = Utterance(
        id="iwslt24_train_clip",
        source_audio=str(source),
        reference_translation="hola",
        provenance="IWSLT test",
        extra={"source_release_split": "train"},
    )
    template = tmp_path / "french.tsv"
    write_reference_template([record], template)
    assert "target_reference" in template.read_text(encoding="utf-8")
    template.write_text(
        "id\ttarget_reference\ttranslator_id\treviewer_id\treference_status\tnotes\n"
        "iwslt24_train_clip\tBonjour\ttranslator-1\treviewer-1\tapproved\tgood\n",
        encoding="utf-8",
    )
    references = read_approved_references(template, {record.id})
    target_root = tmp_path / "targets"
    (target_root / "train").mkdir(parents=True)
    (target_root / "train" / "clip.wav").write_bytes(b"target")
    candidates = make_target_candidates([record], references, target_root, "fr", "voice-v1", "consent-1")
    assert candidates[0].reference_translation == "Bonjour"
    assert candidates[0].extra["target_language"] == "fr"


def test_only_configured_non_spanish_languages_are_valid() -> None:
    assert validate_target_language("hi") == "hi"
    with pytest.raises(ValueError, match="target-language"):
        validate_target_language("es")
