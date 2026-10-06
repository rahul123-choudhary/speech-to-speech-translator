from pathlib import Path

import pytest

from s2st.manifest import Utterance
from s2st.prepare import build_iwslt_candidates, read_approvals, trainable_records, write_review_template


def _record(tmp_path: Path, target_exists: bool = True) -> Utterance:
    source = tmp_path / "source.wav"
    target = tmp_path / "target.wav"
    source.write_bytes(b"source")
    if target_exists:
        target.write_bytes(b"target")
    return Utterance(
        id="item",
        source_audio=str(source),
        target_audio=str(target) if target_exists else None,
        reference_translation="hola",
        provenance="test",
        target_speech_generator="licensed-voice-v1",
        consent_id="consent-1",
    )


def test_trainable_records_require_review_and_target_audio(tmp_path: Path) -> None:
    record = _record(tmp_path)
    approvals = {
        "item": {
            "id": "item",
            "reviewer_id": "reviewer",
            "approved": "yes",
            "translation_fidelity": "5",
            "speech_intelligibility": "5",
            "cultural_appropriateness": "5",
            "notes": "approved",
        }
    }
    accepted = trainable_records([record], approvals)
    assert accepted[0].extra["target_sha256"]
    assert accepted[0].extra["native_review"]["reviewer_id"] == "reviewer"

    with pytest.raises(ValueError, match="No approved"):
        trainable_records([record], {"item": {**approvals["item"], "approved": "no"}})
    with pytest.raises(ValueError, match="no reviewer ID"):
        trainable_records([record], {"item": {**approvals["item"], "reviewer_id": ""}})
    with pytest.raises(ValueError, match="outside 1–5"):
        trainable_records([record], {"item": {**approvals["item"], "adequacy": "0", "translation_fidelity": "0"}})


def test_iwslt_candidate_maps_matching_target_path_and_writes_review_template(tmp_path: Path) -> None:
    corpus, target = tmp_path / "corpus", tmp_path / "targets"
    text = corpus / "train" / "txt"
    wav = corpus / "train" / "wav"
    text.mkdir(parents=True)
    wav.mkdir()
    (text / "segments").write_text("wav/clip.wav SPEAKER 0.0 1.0\n", encoding="utf-8")
    (text / "train.que").write_text("rimay\n", encoding="utf-8")
    (text / "train.spa").write_text("hola\n", encoding="utf-8")
    (wav / "clip.wav").write_bytes(b"source")
    (target / "train").mkdir(parents=True)
    (target / "train" / "clip.wav").write_bytes(b"target")

    records = build_iwslt_candidates(corpus, target, "licensed-voice-v1", "consent-1")
    assert records[0].target_audio == str(target / "train" / "clip.wav")
    template = tmp_path / "review.csv"
    write_review_template(records, template)
    assert "\nno," in template.read_text(encoding="utf-8")
    assert read_approvals(template)["iwslt26_train_clip"]["reviewer_id"] == ""
