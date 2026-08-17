from pathlib import Path

import pytest

from s2st.english import make_english_candidates, read_approved_references, write_reference_template
from s2st.manifest import Utterance


def _source_record(tmp_path: Path) -> Utterance:
    source = tmp_path / "clip.wav"
    source.write_bytes(b"source")
    return Utterance(
        id="iwslt24_train_clip",
        source_audio=str(source),
        reference_translation="hola",
        provenance="IWSLT test",
        extra={"source_release_split": "train"},
    )


def test_english_reference_template_and_candidate_require_human_approval(tmp_path: Path) -> None:
    record = _source_record(tmp_path)
    template = tmp_path / "english.tsv"
    write_reference_template([record], template)
    text = template.read_text(encoding="utf-8")
    assert "english_reference" in text

    template.write_text(
        "id\tenglish_reference\ttranslator_id\treviewer_id\treference_status\tnotes\n"
        "iwslt24_train_clip\tHello\ttranslator-1\treviewer-1\tapproved\tgood\n",
        encoding="utf-8",
    )
    references = read_approved_references(template, {record.id})
    target_root = tmp_path / "targets"
    (target_root / "train").mkdir(parents=True)
    (target_root / "train" / "clip.wav").write_bytes(b"target")
    candidates = make_english_candidates([record], references, target_root, "voice-v1", "consent-1")
    assert candidates[0].reference_translation == "Hello"
    assert candidates[0].extra["target_language"] == "en"

    template.write_text(
        "id\tenglish_reference\ttranslator_id\treviewer_id\treference_status\tnotes\n"
        "iwslt24_train_clip\tHello\t\treviewer-1\tapproved\tmissing translator\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="translator or reviewer"):
        read_approved_references(template, {record.id})
