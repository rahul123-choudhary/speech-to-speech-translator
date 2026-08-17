"""Construct a review-gated Quechua-to-English direct-S2ST candidate corpus.

The bundled IWSLT data supplies Quechua speech with Spanish references only.
This module deliberately does not machine-translate those references: English
references must be provided and approved by identified human reviewers before
they can be paired with licensed English target speech.
"""

import argparse
import csv
from pathlib import Path

from .manifest import Utterance, read_manifest, write_manifest
from .prepare import sha256, write_review_template


REFERENCE_FIELDS = {
    "id",
    "english_reference",
    "translator_id",
    "reviewer_id",
    "reference_status",
    "notes",
}
REFERENCE_COLUMN_ORDER = [
    "id",
    "english_reference",
    "translator_id",
    "reviewer_id",
    "reference_status",
    "notes",
]


def write_reference_template(spanish_candidates: list[Utterance], path: Path) -> None:
    """Create one English-reference row for every source utterance."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REFERENCE_COLUMN_ORDER, delimiter="\t")
        writer.writeheader()
        for record in spanish_candidates:
            writer.writerow(
                {
                    "id": record.id,
                    "english_reference": "",
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
                raise ValueError(f"Duplicate English reference at {path}:{row_number}: {record_id}")
            if row["reference_status"].strip().lower() != "approved":
                continue
            if not row["english_reference"].strip():
                raise ValueError(f"Approved English reference is empty: {record_id}")
            if not row["translator_id"].strip() or not row["reviewer_id"].strip():
                raise ValueError(f"Approved English reference lacks translator or reviewer ID: {record_id}")
            approved[record_id] = row
    if not approved:
        raise ValueError("No approved English references found")
    return approved


def make_english_candidates(
    spanish_candidates: list[Utterance],
    references: dict[str, dict[str, str]],
    target_audio_dir: Path,
    target_speech_generator: str,
    consent_id: str,
) -> list[Utterance]:
    records: list[Utterance] = []
    for source in spanish_candidates:
        reference = references.get(source.id)
        if not reference:
            continue
        split = source.extra["source_release_split"]
        target = target_audio_dir / split / Path(source.source_audio).name
        extra = {
            **source.extra,
            "target_language": "en",
            "english_reference_provenance": {
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
                    "reference_translation": reference["english_reference"].strip(),
                    "provenance": f"{source.provenance}; human-reviewed English reference",
                    "target_speech_generator": target_speech_generator or None,
                    "consent_id": consent_id or None,
                    "extra": extra,
                }
            )
        )
    if not records:
        raise ValueError("No English candidates were created")
    return records


def run(
    spanish_candidates_path: str,
    reference_template: str | None,
    english_references: str | None,
    target_audio_dir: str | None,
    candidates_path: str,
    review_template: str,
    target_speech_generator: str,
    consent_id: str,
) -> None:
    spanish_candidates = list(read_manifest(spanish_candidates_path))
    if reference_template:
        write_reference_template(spanish_candidates, Path(reference_template))
        print(f"english_reference_template={reference_template} rows={len(spanish_candidates)}")
    if not english_references:
        return
    if not target_audio_dir:
        raise ValueError("--target-audio-dir is required when building English candidates")
    references = read_approved_references(Path(english_references), {record.id for record in spanish_candidates})
    candidates = make_english_candidates(
        spanish_candidates,
        references,
        Path(target_audio_dir),
        target_speech_generator,
        consent_id,
    )
    write_manifest(candidates, candidates_path)
    write_review_template(candidates, Path(review_template))
    print(f"english_candidates={len(candidates)} review_template={review_template}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Prepare reviewed Quechua-to-English direct-S2ST candidates")
    parser.add_argument("--spanish-candidates", default="data/manifests/candidates.jsonl")
    parser.add_argument("--reference-template", help="Write a TSV template for human English references")
    parser.add_argument("--english-references", help="Completed, approved English-reference TSV")
    parser.add_argument("--target-audio-dir", help="Licensed English audio root: <split>/<source-file>.wav")
    parser.add_argument("--candidates", default="data/manifests_en/candidates.jsonl")
    parser.add_argument("--review-template", default="data/manifests_en/native_review.csv")
    parser.add_argument("--target-speech-generator", default="")
    parser.add_argument("--consent-id", default="")
    arguments = parser.parse_args()
    run(
        arguments.spanish_candidates,
        arguments.reference_template,
        arguments.english_references,
        arguments.target_audio_dir,
        arguments.candidates,
        arguments.review_template,
        arguments.target_speech_generator,
        arguments.consent_id,
    )
