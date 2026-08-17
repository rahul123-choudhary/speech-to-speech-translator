"""Build a review-gated direct S2ST corpus from an IWSLT Quechua--Spanish release.

This module never synthesizes target speech.  That action requires a separately
licensed voice and native-speaker approval, neither of which can be inferred
from corpus files.  It instead creates auditable candidate records and only
emits trainable manifests when approved target waveforms are supplied.
"""

import argparse
import csv
import hashlib
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


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def duration_seconds(path: str) -> float:
    import torchaudio

    info = torchaudio.info(path)
    return info.num_frames / info.sample_rate


def stable_bucket(value: str) -> int:
    return int(hashlib.sha256(value.encode()).hexdigest(), 16) % 10


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def build_iwslt_candidates(
    corpus_dir: Path,
    target_audio_dir: Path,
    target_speech_generator: str,
    consent_id: str,
) -> list[Utterance]:
    """Read the IWSLT constrained layout without treating text as model input."""
    records: list[Utterance] = []
    for split_dir in sorted(path for path in corpus_dir.iterdir() if path.is_dir()):
        split = split_dir.name
        text_dir, wav_dir = split_dir / "txt", split_dir / "wav"
        segments = read_lines(text_dir / "segments")
        que = read_lines(text_dir / f"{split}.que") if (text_dir / f"{split}.que").exists() else []
        spa = read_lines(text_dir / f"{split}.spa")
        if len(segments) != len(spa) or que and len(segments) != len(que):
            raise ValueError(f"Misaligned files in {split_dir}")
        for index, segment in enumerate(segments):
            fields = segment.split()
            if len(fields) < 2:
                raise ValueError(f"Malformed segment at {split_dir}/txt/segments:{index + 1}")
            relative_audio, speaker_id = fields[0], fields[1]
            source = wav_dir.parent / relative_audio
            if not source.is_file():
                raise FileNotFoundError(f"Missing source audio: {source}")
            target = target_audio_dir / split / Path(relative_audio).name
            records.append(
                Utterance(
                    id=f"iwslt24_{split}_{Path(relative_audio).stem}",
                    source_audio=str(source),
                    target_audio=str(target) if target.is_file() else None,
                    reference_translation=spa[index],
                    source_transcript=que[index] if que else None,
                    speaker_id=speaker_id,
                    split=split,
                    provenance="IWSLT 2024 Quechua-Spanish constrained / Siminchik",
                    target_speech_generator=target_speech_generator or None,
                    consent_id=consent_id or None,
                    extra={
                        "dialect": "southern_quechua",
                        "source_sha256": sha256(source),
                        "source_release_split": split,
                    },
                )
            )
    return records


def write_review_template(records: list[Utterance], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=sorted(APPROVAL_FIELDS))
        writer.writeheader()
        for record in records:
            writer.writerow({"id": record.id, "approved": "no"})


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
        if not record.target_speech_generator or not record.consent_id:
            raise ValueError(f"Approved record lacks generator provenance or consent: {record.id}")
        extra = {
            **record.extra,
            "target_sha256": sha256(Path(record.target_audio)),
            "native_review": {key: review[key] for key in APPROVAL_FIELDS - {"id"}},
        }
        accepted.append(record.model_copy(update={"extra": extra}))
    if not accepted:
        raise ValueError("No approved records with target speech; manifests were not created")
    return accepted


def make_splits(records: list[Utterance], maximum_seconds: float) -> dict[str, list[Utterance]]:
    """Keep source splits only when they are speaker-disjoint; otherwise re-split."""
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
    source_split_is_safe = bool(speaker_splits) and all(len(names) == 1 for names in speaker_splits.values())
    if not source_split_is_safe:
        print("source split has speaker overlap or lacks speaker metadata; using deterministic speaker-disjoint split")
    for record in selected:
        if source_split_is_safe and record.split in source_name:
            split = source_name[record.split]
        else:
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
    parser = argparse.ArgumentParser(description="Prepare review-gated manifests for direct Quechua S2ST")
    parser.add_argument("--input", help="Candidate JSONL input")
    parser.add_argument("--iwslt-constrained-dir", help="Directory containing train/valid/test IWSLT folders")
    parser.add_argument("--target-audio-dir", help="Root containing approved Spanish audio as <split>/<source-name>.wav")
    parser.add_argument("--candidates", default="data/manifests/candidates.jsonl")
    parser.add_argument("--review-template", default="data/manifests/native_review.csv")
    parser.add_argument("--target-speech-generator", default="")
    parser.add_argument("--consent-id", default="")
    parser.add_argument("--approvals", help="Completed native-review CSV")
    parser.add_argument("--output", default="data/manifests")
    parser.add_argument("--maximum-hours", type=float, default=1.67)
    parser.add_argument("--sync-atlas", action="store_true")
    arguments = parser.parse_args()
    if arguments.iwslt_constrained_dir:
        if not arguments.target_audio_dir:
            parser.error("--target-audio-dir is required with --iwslt-constrained-dir")
        candidates = build_iwslt_candidates(
            Path(arguments.iwslt_constrained_dir),
            Path(arguments.target_audio_dir),
            arguments.target_speech_generator,
            arguments.consent_id,
        )
        write_manifest(candidates, arguments.candidates)
        if not arguments.approvals:
            write_review_template(candidates, Path(arguments.review_template))
            print(f"candidates={len(candidates)} review_template={arguments.review_template}")
        else:
            print(f"candidates={len(candidates)} using_approvals={arguments.approvals}")
        if not arguments.approvals:
            raise SystemExit("Candidates written. Add licensed target audio, complete native review, then rerun this command with --approvals.")
        input_path = arguments.candidates
    elif arguments.input:
        input_path = arguments.input
    else:
        parser.error("Provide --input or --iwslt-constrained-dir")
    run(input_path, arguments.output, arguments.maximum_hours, arguments.approvals, arguments.sync_atlas)
