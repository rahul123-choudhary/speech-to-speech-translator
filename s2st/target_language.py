"""Review-gated data preparation for non-Spanish direct S2ST targets.

The included corpus provides Quechua speech and Spanish references only. This
module creates the review workflow for a *separate* target language; it never
derives target speech through Spanish during training or inference.
"""

import argparse
import csv
from pathlib import Path

from .languages import TARGET_LANGUAGES
from .manifest import Utterance, read_manifest, write_manifest
from .prepare import write_review_template


REFERENCE_FIELDS = {
    "id",
    "target_reference",
    "translator_id",
    "reviewer_id",
    "reference_status",
    "notes",
}
REFERENCE_COLUMN_ORDER = [
    "id",
    "target_reference",
    "translator_id",
    "reviewer_id",
    "reference_status",
    "notes",
]
NON_SPANISH_TARGETS = {"en", "hi", "fr", "pt"}


def validate_target_language(target_language: str) -> str:
    if target_language not in NON_SPANISH_TARGETS:
        supported = ", ".join(sorted(NON_SPANISH_TARGETS))
        raise ValueError(f"--target-language must be one of: {supported}")
    return target_language


def write_reference_template(source_candidates: list[Utterance], path: Path) -> None:
    """Write one human-translation review row per Quechua source utterance."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REFERENCE_COLUMN_ORDER, delimiter="\t")
        writer.writeheader()
        for record in source_candidates:
            writer.writerow(
                {
                    "id": record.id,
                    "target_reference": "",
                    "translator_id": "",
                    "reviewer_id": "",
                    "reference_status": "pending",
                    "notes": "",
                }
            )


def read_approved_references(path: Path, candidate_ids: set[str]) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if not reader.fieldnames or not REFERENCE_FIELDS.issubset(reader.fieldnames):
            fields = ", ".join(sorted(REFERENCE_FIELDS))
            raise ValueError(f"{path} must be a tab-separated file containing: {fields}")
        approved: dict[str, dict[str, str]] = {}
        for row_number, row in enumerate(reader, 2):
            record_id = row["id"].strip()
            if record_id not in candidate_ids:
                raise ValueError(f"Unknown candidate ID at {path}:{row_number}: {record_id}")
            if record_id in approved:
                raise ValueError(f"Duplicate target reference at {path}:{row_number}: {record_id}")
            if row["reference_status"].strip().lower() != "approved":
                continue
            if not row["target_reference"].strip():
                raise ValueError(f"Approved target reference is empty: {record_id}")
            if not row["translator_id"].strip() or not row["reviewer_id"].strip():
                raise ValueError(f"Approved target reference lacks translator or reviewer ID: {record_id}")
            approved[record_id] = row
    if not approved:
        raise ValueError("No approved target references found")
    return approved


def make_target_candidates(
    source_candidates: list[Utterance],
    references: dict[str, dict[str, str]],
    target_audio_dir: Path,
    target_language: str,
    target_speech_generator: str,
    consent_id: str,
) -> list[Utterance]:
    """Pair approved text with licensed target-language speech by utterance ID."""
    target_language = validate_target_language(target_language)
    records: list[Utterance] = []
    for source in source_candidates:
        reference = references.get(source.id)
        if not reference:
            continue
        split = source.extra["source_release_split"]
        target = target_audio_dir / split / Path(source.source_audio).name
        extra = {
            **source.extra,
            "target_language": target_language,
            "target_reference_provenance": {
                "translator_id": reference["translator_id"],
                "reviewer_id": reference["reviewer_id"],
                "status": reference["reference_status"],
                "notes": reference["notes"],
            },
        }
        records.append(
            source.model_copy(
                update={
                    "target_audio": str(target) if target.is_file() else None,
                    "reference_translation": reference["target_reference"].strip(),
                    "provenance": f"{source.provenance}; human-reviewed {TARGET_LANGUAGES[target_language]['name']} reference",
                    "target_speech_generator": target_speech_generator or None,
                    "consent_id": consent_id or None,
                    "extra": extra,
                }
            )
        )
    if not records:
        raise ValueError("No target-language candidates were created")
    return records


def run(
    source_candidates_path: str,
    target_language: str,
    reference_template: str | None,
    target_references: str | None,
    target_audio_dir: str | None,
    candidates_path: str,
    review_template: str,
    target_speech_generator: str,
    consent_id: str,
) -> None:
    target_language = validate_target_language(target_language)
    source_candidates = list(read_manifest(source_candidates_path))
    if reference_template:
        write_reference_template(source_candidates, Path(reference_template))
        print(f"reference_template={reference_template} rows={len(source_candidates)}")
    if not target_references:
        return
    if not target_audio_dir:
        raise ValueError("--target-audio-dir is required when building candidates")
    references = read_approved_references(Path(target_references), {record.id for record in source_candidates})
    candidates = make_target_candidates(
        source_candidates,
        references,
        Path(target_audio_dir),
        target_language,
        target_speech_generator,
        consent_id,
    )
    write_manifest(candidates, candidates_path)
    write_review_template(candidates, Path(review_template))
    print(f"target_language={target_language} candidates={len(candidates)} review_template={review_template}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare reviewed direct-S2ST target-language candidates")
    parser.add_argument("--source-candidates", default="data/manifests/candidates.jsonl")
    parser.add_argument("--target-language", required=True, choices=sorted(NON_SPANISH_TARGETS))
    parser.add_argument("--reference-template", help="Write a TSV template for human target-language references")
    parser.add_argument("--target-references", help="Completed, approved target-reference TSV")
    parser.add_argument("--target-audio-dir", help="Licensed target-audio root: <split>/<source-file>.wav")
    parser.add_argument("--candidates", help="Output candidates JSONL")
    parser.add_argument("--review-template", help="Output native-review CSV")
    parser.add_argument("--target-speech-generator", default="")
    parser.add_argument("--consent-id", default="")
    arguments = parser.parse_args()
    output_dir = Path(f"data/manifests_{arguments.target_language}")
    run(
        arguments.source_candidates,
        arguments.target_language,
        arguments.reference_template,
        arguments.target_references,
        arguments.target_audio_dir,
        arguments.candidates or str(output_dir / "candidates.jsonl"),
        arguments.review_template or str(output_dir / "native_review.csv"),
        arguments.target_speech_generator,
        arguments.consent_id,
    )
