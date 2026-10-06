"""Build a review-gated direct S2ST corpus from an IWSLT speech-to-speech release.

This module never synthesizes unverified speech. It creates auditable candidate records
and emits trainable manifests when approved target waveforms are supplied.
"""

import argparse
import csv
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path

from .manifest import Utterance, read_manifest, write_manifest


APPROVAL_FIELDS = {
    "id",
    "reviewer_id",
    "approved",
    "translation_fidelity",
    "speech_intelligibility",
    "cultural_appropriateness",
    "notes",
}
REVIEW_CONTEXT_FIELDS = {
    "source_audio",
    "target_audio",
    "source_transcript",
    "reference_translation",
    "speaker_id",
    "split",
    "reference_source",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def duration_seconds(path: str) -> float:
    import soundfile

    info = soundfile.info(path)
    return info.frames / info.samplerate


def stable_bucket(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest(), 16) % 10


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def build_iwslt_candidates(
    corpus_dir: Path,
    target_audio_dir: Path | None,
    target_speech_generator: str,
    consent_id: str,
) -> list[Utterance]:
    """Index IWSLT 2026 audio/text rows without treating text as target speech.

    This release supplies source audio and translation text, not paired target
    recordings. ``target_audio`` therefore stays empty unless separately supplied.
    """
    records: list[Utterance] = []
    for split_dir in sorted(path for path in corpus_dir.iterdir() if path.is_dir()):
        split = split_dir.name
        text_dir, wav_dir = split_dir / "txt", split_dir / "wav"
        if not text_dir.exists() or not wav_dir.exists():
            continue
        segments = read_lines(text_dir / "segments") if (text_dir / "segments").exists() else []
        src_lines = read_lines(text_dir / f"{split}.src") if (text_dir / f"{split}.src").exists() else []
        tgt_lines = read_lines(text_dir / f"{split}.tgt") if (text_dir / f"{split}.tgt").exists() else []
        if not tgt_lines and (text_dir / f"{split}.en").exists():
            tgt_lines = read_lines(text_dir / f"{split}.en")

        for index, segment in enumerate(segments):
            fields = segment.split()
            if len(fields) < 2:
                continue
            relative_audio, speaker_id = fields[0], fields[1]
            source = wav_dir.parent / relative_audio
            if not source.is_file():
                source = wav_dir / Path(relative_audio).name
            if not source.is_file():
                continue
            target = (
                target_audio_dir / split / Path(relative_audio).name
                if target_audio_dir is not None
                else None
            )
            records.append(
                Utterance(
                    id=f"iwslt26_{split}_{Path(relative_audio).stem}",
                    source_audio=str(source),
                    target_audio=str(target) if target is not None and target.is_file() else None,
                    reference_translation=tgt_lines[index] if index < len(tgt_lines) else "",
                    source_transcript=src_lines[index] if index < len(src_lines) else None,
                    speaker_id=speaker_id,
                    split=split,
                    provenance="IWSLT 2026 speech-to-speech release",
                    target_speech_generator=target_speech_generator or None,
                    consent_id=consent_id or None,
                    extra={
                        "dataset_status": "candidate_unreviewed",
                        "target_audio_available": bool(target and target.is_file()),
                        "source_sha256": sha256(source),
                        "source_release_split": split,
                    },
                )
            )
    return records


def write_review_template(records: list[Utterance], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted(APPROVAL_FIELDS | REVIEW_CONTEXT_FIELDS))
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "id": record.id,
                    "approved": "no",
                    "source_audio": record.source_audio,
                    "target_audio": record.target_audio or "",
                    "source_transcript": record.source_transcript or "",
                    "reference_translation": record.reference_translation,
                    "speaker_id": record.speaker_id or "",
                    "split": record.split or "",
                    "reference_source": record.extra.get("reference_source", ""),
                }
            )


def read_approvals(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not APPROVAL_FIELDS.issubset(reader.fieldnames):
            raise ValueError(f"{path} must contain: {', '.join(sorted(APPROVAL_FIELDS))}")
        approvals: dict[str, dict[str, str]] = {}
        for row_number, row in enumerate(reader, 2):
            record_id = row["id"].strip()
            if not record_id:
                raise ValueError(f"Missing id at {path}:{row_number}")
            if record_id in approvals:
                raise ValueError(f"Duplicate review for {record_id} at {path}:{row_number}")
            approvals[record_id] = row
        return approvals


def validate_approved_review(record_id: str, review: dict[str, str]) -> None:
    if not review["reviewer_id"].strip():
        raise ValueError(f"Approved record has no reviewer ID: {record_id}")
    for field in ("translation_fidelity", "speech_intelligibility", "cultural_appropriateness"):
        try:
            rating = int(review[field])
        except ValueError as error:
            raise ValueError(f"Approved record has invalid {field}: {record_id}") from error
        if rating not in range(1, 6):
            raise ValueError(f"Approved record has {field} outside 1–5: {record_id}")


def trainable_records(records: list[Utterance], approvals: dict[str, dict[str, str]]) -> list[Utterance]:
    accepted: list[Utterance] = []
    for record in records:
        review = approvals.get(record.id)
        if not review or review["approved"].strip().lower() not in {"yes", "true", "1"}:
            continue
        validate_approved_review(record.id, review)
        if not record.target_audio or not Path(record.target_audio).is_file():
            raise FileNotFoundError(f"Approved record has no target speech: {record.id}")
        if not (record.target_speech_generator or record.extra.get("target_audio_provenance")):
            raise ValueError(f"Approved record lacks target-audio provenance: {record.id}")
        if not record.consent_id:
            raise ValueError(f"Approved record lacks a consent/authorization ID: {record.id}")
        extra = {
            **record.extra,
            "target_sha256": sha256(Path(record.target_audio)),
            "native_review": {key: review[key] for key in APPROVAL_FIELDS - {"id"}},
        }
        extra["dataset_status"] = "approved_for_training"
        accepted.append(record.model_copy(update={"extra": extra}))
    if not accepted:
        raise ValueError("No approved records with target speech; manifests were not created")
    return accepted


def make_splits(records: list[Utterance], maximum_seconds: float) -> dict[str, list[Utterance]]:
    """Keep official test data and create a speaker-held-out validation split."""
    selected: list[Utterance] = []
    total = 0.0
    for record in sorted(records, key=lambda item: item.id):
        seconds = duration_seconds(record.source_audio)
        if seconds <= 0 or seconds > 15 or total + seconds > maximum_seconds:
            continue
        selected.append(record)
        total += seconds
    splits = {"train": [], "validation": [], "test": []}
    source_name = {"train": "train", "valid": "validation", "validation": "validation", "test": "test"}
    speaker_splits: dict[str, set[str]] = defaultdict(set)
    for record in selected:
        if record.split in source_name and record.speaker_id:
            speaker_splits[record.speaker_id].add(source_name[record.split])
    source_split_is_safe = (
        bool(speaker_splits)
        and all(len(names) == 1 for names in speaker_splits.values())
        and {source_name.get(record.split) for record in selected} >= {"train", "validation", "test"}
    )
    if source_split_is_safe:
        for record in selected:
            split = source_name[record.split]
            splits[split].append(record.model_copy(update={"split": split}))
    else:
        train_records = [record for record in selected if record.split == "train"]
        test_records = [record for record in selected if record.split == "test"]
        validation_records = [record for record in selected if record.split in {"valid", "validation"}]
        if test_records and not validation_records:
            test_text = {
                " ".join(record.source_transcript.split()).casefold()
                for record in test_records
                if record.source_transcript
            }
            before = len(train_records)
            if test_text:
                train_records = [
                    record
                    for record in train_records
                    if not record.source_transcript
                    or " ".join(record.source_transcript.split()).casefold() not in test_text
                ]
            removed_test_overlap = before - len(train_records)
            train_speakers = sorted({record.speaker_id for record in train_records if record.speaker_id})
            if len(train_speakers) < 2:
                raise ValueError("Cannot create speaker-disjoint validation split: need at least two identified train speakers")
            validation_speaker = min(train_speakers, key=stable_bucket)
            validation_records = [record for record in train_records if record.speaker_id == validation_speaker]
            train_records = [record for record in train_records if record.speaker_id != validation_speaker]
            validation_text = {" ".join(record.source_transcript.split()).casefold() for record in validation_records if record.source_transcript}
            if validation_text:
                # Keep identical text out of train to reduce content leakage across the held-out speaker.
                train_records = [record for record in train_records if not record.source_transcript or " ".join(record.source_transcript.split()).casefold() not in validation_text]
            print(f"validation_speaker={validation_speaker}; removed_test_prompt_overlap={removed_test_overlap}; repeated prompts removed from train")
            for record in train_records:
                splits["train"].append(record.model_copy(update={"split": "train"}))
            for record in validation_records:
                splits["validation"].append(record.model_copy(update={"split": "validation"}))
            for record in test_records:
                splits["test"].append(record.model_copy(update={"split": "test"}))
        else:
            print("source split has speaker overlap or lacks a validation split; using deterministic speaker-disjoint split")
            for record in selected:
                bucket = stable_bucket(record.speaker_id or record.id)
                split = "test" if bucket == 0 else "validation" if bucket == 1 else "train"
                splits[split].append(record.model_copy(update={"split": split}))
    if not all(splits.values()):
        raise ValueError("Need approved records in every train/validation/test split")
    print(f"selected_seconds={total:.1f}")
    return splits


def sync_corpus_metadata(records: list[Utterance]) -> None:
    from .settings import get_settings
    from .storage import ResearchStore

    store = ResearchStore(get_settings())
    for record in records:
        store.upsert_corpus_metadata(record.model_dump())


def run(input_path: str, output_dir: str, maximum_hours: float, approvals_path: str | None, sync_atlas: bool) -> None:
    records = list(read_manifest(input_path))
    if approvals_path:
        records = trainable_records(records, read_approvals(Path(approvals_path)))
    elif any(not record.target_audio for record in records):
        raise ValueError("Candidate records require --approvals before training manifests can be made")
    splits = make_splits(records, maximum_hours * 3600)
    for name, items in splits.items():
        write_manifest(items, Path(output_dir) / f"{name}.jsonl")
        print(f"{name}={len(items)}")
    if sync_atlas:
        sync_corpus_metadata(records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare review-gated manifests for direct S2ST")
    parser.add_argument("--input", help="Candidate JSONL input")
    parser.add_argument(
        "--iwslt-dir",
        "--iwslt-constrained-dir",
        dest="iwslt_constrained_dir",
        help="IWSLT speech root containing train/valid/test folders",
    )
    parser.add_argument("--target-audio-dir", help="Optional target audio root as <split>/<source-name>.wav")
    parser.add_argument("--candidates", help="Output candidate JSONL path")
    parser.add_argument("--review-template", help="Output human-review CSV path")
    parser.add_argument("--target-speech-generator", default="")
    parser.add_argument("--consent-id", default="")
    parser.add_argument("--approvals", help="Completed native-review CSV")
    parser.add_argument("--output", default="data/manifests")
    parser.add_argument("--maximum-hours", type=float, default=1.67)
    parser.add_argument("--sync-atlas", action="store_true")
    arguments = parser.parse_args()
    if arguments.iwslt_constrained_dir:
        candidates_path = Path(arguments.candidates or "data/processed/iwslt2026/candidates.jsonl")
        review_path = Path(arguments.review_template or "data/processed/iwslt2026/native_review.csv")
        candidates = build_iwslt_candidates(
            Path(arguments.iwslt_constrained_dir),
            Path(arguments.target_audio_dir) if arguments.target_audio_dir else None,
            arguments.target_speech_generator,
            arguments.consent_id,
        )
        write_manifest(candidates, candidates_path)
        if not arguments.approvals:
            write_review_template(candidates, review_path)
            print(f"candidate_rows={len(candidates)} candidates={candidates_path} review_template={review_path}")
            print("Unreviewed rows contain source speech and text only; they are not direct S2ST training pairs.")
            raise SystemExit(0)
        else:
            print(f"candidate_rows={len(candidates)} using_approvals={arguments.approvals}")
        input_path = str(candidates_path)
    elif arguments.input:
        input_path = arguments.input
    else:
        parser.error("Provide --input or --iwslt-constrained-dir")
    run(input_path, arguments.output, arguments.maximum_hours, arguments.approvals, arguments.sync_atlas)
