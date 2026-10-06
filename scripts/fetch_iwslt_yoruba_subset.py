"""Fetch a compact, review-gated Yorùbá→English subset from NaijaS2ST.

The full upstream release is too large to copy into this repository. This
script pages the Hugging Face dataset viewer for metadata and downloads only a
small set of matched training utterances. It never marks recordings approved.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests


DATASET = "McGill-NLP/NaijaS2ST"
DATASET_REVISION = "4fef5310ef98b8c703e490ea9908100f152ad5b3"
VIEWER = "https://datasets-server.huggingface.co/rows"
SOURCE_START, SOURCE_END = 36_000, 52_000
ENGLISH_START, ENGLISH_END = 52_000, 58_000
RECORDS_PER_PAGE = 100
LICENSE = "CC BY 4.0"


def _get_json(
    session: requests.Session,
    url: str,
    params: dict[str, Any],
    scan_depth: int = 0,
) -> dict[str, Any]:
    for attempt in range(8):
        response = session.get(url, params=params, timeout=(15, 120))
        if response.status_code == 500 and "Scan size limit exceeded" in response.text:
            length = int(params["length"])
            if length <= 1 or scan_depth >= 8:
                response.raise_for_status()
            left_length = length // 2
            right_length = length - left_length
            first = _get_json(
                session,
                url,
                {**params, "length": left_length},
                scan_depth + 1,
            )
            second = _get_json(
                session,
                url,
                {**params, "offset": int(params["offset"]) + left_length, "length": right_length},
                scan_depth + 1,
            )
            return {**first, "rows": first.get("rows", []) + second.get("rows", [])}
        if response.status_code == 429 or response.status_code >= 500:
            time.sleep(min(60, 2**attempt))
            continue
        response.raise_for_status()
        return response.json()
    raise RuntimeError(f"Dataset viewer remained unavailable after retries: {url}")


def _pages(session: requests.Session, split: str, start: int, stop: int, cache_dir: Path):
    offsets = list(range(start, stop, RECORDS_PER_PAGE))
    local = threading.local()
    cache_dir.mkdir(parents=True, exist_ok=True)

    def load(offset: int) -> list[dict[str, Any]]:
        cache_path = cache_dir / f"{split}_{offset:06d}.json"
        if cache_path.is_file():
            return json.loads(cache_path.read_text(encoding="utf-8"))
        if not hasattr(local, "session"):
            local.session = requests.Session()
            local.session.headers.update(session.headers)
        payload = _get_json(
            local.session,
            VIEWER,
            {
                "dataset": DATASET,
                "config": "default",
                "split": split,
                "offset": offset,
                "length": min(RECORDS_PER_PAGE, stop - offset),
            },
        )
        rows = [item["row"] for item in payload.get("rows", [])]
        temporary = cache_path.with_suffix(".json.part")
        temporary.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
        temporary.replace(cache_path)
        return rows

    with ThreadPoolExecutor(max_workers=2) as executor:
        for page_number, rows in enumerate(executor.map(load, offsets), 1):
            if page_number % 10 == 0:
                print(f"metadata_pages={page_number}/{len(offsets)} split={split}", flush=True)
            yield from rows


def _audio_url(row: dict[str, Any]) -> str:
    audio = row.get("audio")
    if isinstance(audio, list) and audio:
        url = audio[0].get("src", "")
    elif isinstance(audio, dict):
        url = audio.get("src", "") or audio.get("url", "")
    else:
        url = ""
    if urlparse(url).scheme != "https":
        raise ValueError(f"Missing secure audio URL for {row.get('text_id')}")
    return url


def _download(session: requests.Session, url: str, destination: Path) -> None:
    if destination.exists() and destination.stat().st_size > 44:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    for attempt in range(8):
        with session.get(url, stream=True, timeout=(20, 180)) as response:
            if response.status_code == 403:
                match = re.search(r"/default/([^/]+)/(\d+)/audio", url)
                if match:
                    split, offset = match.group(1), int(match.group(2))
                    payload = _get_json(
                        session,
                        VIEWER,
                        {"dataset": DATASET, "config": "default", "split": split, "offset": offset, "length": 1},
                    )
                    rows = payload.get("rows", [])
                    if rows:
                        url = _audio_url(rows[0]["row"])
                        continue
            if response.status_code == 429 or response.status_code >= 500:
                time.sleep(min(60, 2**attempt))
                continue
            response.raise_for_status()
            with temporary.open("wb") as output:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        output.write(chunk)
            break
    else:
        raise RuntimeError(f"Audio download remained unavailable: {destination.name}")
    if temporary.stat().st_size <= 44:
        temporary.unlink(missing_ok=True)
        raise ValueError(f"Downloaded audio is empty or invalid: {destination.name}")
    temporary.replace(destination)


def _split_for(text_id: str) -> str:
    bucket = int(hashlib.sha256(text_id.encode("utf-8")).hexdigest()[:8], 16) % 10
    return "test" if bucket == 0 else "validation" if bucket == 1 else "train"


def _select_pairs(source_rows: list[dict[str, Any]], english_rows: list[dict[str, Any]], hours: float):
    targets: dict[str, dict[str, Any]] = {}
    for row in english_rows:
        text_id = row.get("text_id", "")
        if text_id.startswith("E"):
            targets.setdefault(text_id, row)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in source_rows:
        source_id = row.get("text_id", "")
        target_id = "E" + source_id[1:] if source_id.startswith("Y") else ""
        if target_id in targets:
            grouped[source_id].append(row)

    candidates = [
        (text_id, rows, targets["E" + text_id[1:]])
        for text_id, rows in sorted(grouped.items())
        if len({row.get("user_id") for row in rows}) >= 3
    ]
    random.Random(20260926).shuffle(candidates)

    selected = []
    total_seconds = 0.0
    target_seconds = hours * 3600
    for text_id, rows, target in candidates:
        rows = sorted(rows, key=lambda row: (row.get("user_id", ""), row.get("recorded_at", "")))[:3]
        pair_seconds = sum(float(row.get("duration", 0)) for row in rows) + float(target.get("duration", 0))
        if not pair_seconds:
            continue
        if selected and total_seconds + pair_seconds > target_seconds:
            continue
        selected.append((text_id, rows, target))
        total_seconds += pair_seconds
        if total_seconds >= target_seconds * 0.98:
            break
    return selected, total_seconds, len(grouped)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def fetch(output: Path, hours: float, consent_id: str | None) -> None:
    session = requests.Session()
    session.headers.update({"User-Agent": "STS-Yoruba-S2ST/0.1 (research data preparation)"})

    output.mkdir(parents=True, exist_ok=True)
    cache_dir = output / "metadata_cache"
    print("Fetching Yorùbá source metadata; this is several hundred small viewer requests.", flush=True)
    source_rows = [
        row for row in _pages(session, "train", SOURCE_START, SOURCE_END, cache_dir)
        if row.get("language", "").lower() == "yoruba"
    ]
    print(f"source_rows={len(source_rows)}; fetching English target metadata.", flush=True)
    english_rows = [
        row for row in _pages(session, "train", ENGLISH_START, ENGLISH_END, cache_dir)
        if row.get("language", "").lower() == "english"
    ]
    selected, estimated_seconds, matching_ids = _select_pairs(source_rows, english_rows, hours)
    if not selected:
        raise RuntimeError("No matched Yorùbá/English triplets found in the selected release ranges")

    raw_root = output / "raw"
    source_root, target_root = raw_root / "yoruba", raw_root / "english"
    processed_root = output / "processed"
    processed_root.mkdir(parents=True, exist_ok=True)

    target_files: dict[str, Path] = {}
    for _, _, target in selected:
        text_id = target["text_id"]
        if text_id in target_files:
            continue
        filename = f"{text_id}_{target['user_id']}.wav"
        path = target_root / filename
        _download(session, _audio_url(target), path)
        target_files[text_id] = path

    records = []
    seen_speakers = set()
    for text_id, rows, target in selected:
        split = _split_for(text_id)
        for source in rows:
            speaker = source["user_id"]
            seen_speakers.add(speaker)
            source_path = source_root / f"{source['text_id']}_{speaker}.wav"
            _download(session, _audio_url(source), source_path)
            records.append(
                {
                    "id": f"naijas2st_{split}_{source['text_id']}_{speaker}",
                    "source_audio": str(source_path.resolve()),
                    "target_audio": str(target_files[target["text_id"]].resolve()),
                    "reference_translation": target["text"],
                    "source_transcript": source["text"],
                    "speaker_id": speaker,
                    "split": split,
                    "provenance": f"{DATASET}@{DATASET_REVISION}; IWSLT 2026 Yorùbá→English S2S training release; {LICENSE}",
                    "consent_id": consent_id or None,
                    "extra": {
                        "dataset_status": "candidate_unreviewed",
                        "source_release_split": "train",
                        "split_method": "deterministic text-id holdout from official train split (80/10/10 buckets)",
                        "source_text_id": source["text_id"],
                        "target_text_id": target["text_id"],
                        "source_audio_provenance": "original recorded Yorùbá speech",
                        "target_audio_provenance": "original recorded English speech from the paired IWSLT release",
                        "dataset_license": LICENSE,
                        "source_duration_seconds": float(source.get("duration", 0)),
                        "target_duration_seconds": float(target.get("duration", 0)),
                        "source_sha256": _sha256(source_path),
                        "target_sha256": _sha256(target_files[target["text_id"]]),
                    },
                }
            )

    manifest = processed_root / "candidates.jsonl"
    with manifest.open("w", encoding="utf-8") as out:
        for record in records:
            out.write(json.dumps(record, ensure_ascii=False) + "\n")

    review = processed_root / "native_review.csv"
    fields = [
        "id", "reviewer_id", "approved", "translation_fidelity", "speech_intelligibility",
        "cultural_appropriateness", "notes", "source_audio", "target_audio", "source_transcript",
        "reference_translation", "speaker_id", "split", "reference_source",
    ]
    with review.open("w", newline="", encoding="utf-8") as out:
        writer = csv.DictWriter(out, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "id": record["id"],
                    "reviewer_id": "",
                    "approved": "no",
                    "translation_fidelity": "",
                    "speech_intelligibility": "",
                    "cultural_appropriateness": "",
                    "notes": "",
                    "source_audio": record["source_audio"],
                    "target_audio": record["target_audio"],
                    "source_transcript": record["source_transcript"],
                    "reference_translation": record["reference_translation"],
                    "speaker_id": record["speaker_id"],
                    "split": record["split"],
                    "reference_source": "IWSLT paired recording metadata",
                }
            )

    readme = output / "README.md"
    readme.write_text(
        "# IWSLT 2026 Yorùbá→English subset\n\n"
        f"Source: [{DATASET}](https://huggingface.co/datasets/{DATASET}), revision `{DATASET_REVISION}`. "
        "This is a small sample of the official training split, not a full copy of the upstream 85 GB release.\n\n"
        f"License shown on the upstream dataset card: {LICENSE} ([license text](https://creativecommons.org/licenses/by/4.0/)). "
        "Retain attribution and the dataset citation when using these files.\n\n"
        f"Selected {len(selected)} distinct source text IDs, {len(records)} Yorùbá source recordings from "
        f"{len(seen_speakers)} speakers, and {len(target_files)} English recordings. Estimated total recorded "
        f"audio: {estimated_seconds / 3600:.2f} hours (metadata duration sum). The upstream source has "
        f"{len(source_rows)} Yorùbá rows and {matching_ids} source IDs with paired English rows in the scanned ranges.\n\n"
        "All records are candidate-only. The review CSV starts with `approved=no`; native-speaker review and "
        "project-level authorization/consent must be documented before producing trainable manifests. The "
        "provisional validation and test groups are sentence-disjoint buckets drawn from the official train split, "
        "not the official IWSLT dev/test sets.\n",
        encoding="utf-8",
    )
    print(f"candidate_rows={len(records)} source_text_ids={len(selected)} target_files={len(target_files)}")
    print(f"speakers={len(seen_speakers)} estimated_total_hours={estimated_seconds / 3600:.2f}")
    print(f"manifest={manifest} review={review} raw={raw_root}")
    print("status=candidate_unreviewed; native-speaker review and documented authorization are still required")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/iwslt2026_yoruba"))
    parser.add_argument("--hours", type=float, default=2.0, help="Maximum approximate hours including both sides of each pair")
    parser.add_argument(
        "--consent-id",
        default="",
        help="Existing project authorization/consent record ID; do not invent one",
    )
    args = parser.parse_args()
    if args.hours <= 0:
        parser.error("--hours must be positive")
    fetch(args.output, args.hours, args.consent_id.strip() or None)


if __name__ == "__main__":
    main()
