"""Create clearly labelled Spanish-to-English drafts for human review.

This is an offline corpus-construction helper, never part of live inference.
Its output has ``reference_status=machine_draft`` and cannot enter the English
direct-S2ST manifest until an identified translator and reviewer approve it.
"""

import argparse
import csv
from pathlib import Path

from .english import REFERENCE_COLUMN_ORDER
from .manifest import read_manifest


MODEL_NAME = "facebook/nllb-200-distilled-600M"


def write_drafts(records: list[dict[str, str]], path: Path, model_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=REFERENCE_COLUMN_ORDER, delimiter="\t")
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "id": record["id"],
                    "english_reference": record["english_reference"],
                    "translator_id": f"machine:{model_name}",
                    "reviewer_id": "",
                    "reference_status": "machine_draft",
                    "notes": "Offline Spanish-to-English draft. Human translation and review required before use.",
                }
            )


def translate_spanish_references(
    candidates_path: str,
    output_path: str,
    model_name: str = MODEL_NAME,
    batch_size: int = 4,
    device: str = "cpu",
) -> None:
    """Translate IWSLT Spanish references into drafts using local NLLB weights."""
    import torch
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    records = list(read_manifest(candidates_path))
    tokenizer = AutoTokenizer.from_pretrained(model_name, src_lang="spa_Latn")
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name).to(device).eval()
    forced_bos_token_id = tokenizer.convert_tokens_to_ids("eng_Latn")
    drafts: list[dict[str, str]] = []
    with torch.inference_mode():
        for start in range(0, len(records), batch_size):
            batch = records[start : start + batch_size]
            inputs = tokenizer(
                [record.reference_translation for record in batch],
                return_tensors="pt",
                padding=True,
                truncation=True,
            ).to(device)
            generated = model.generate(**inputs, forced_bos_token_id=forced_bos_token_id, max_new_tokens=128)
            translations = tokenizer.batch_decode(generated, skip_special_tokens=True)
            drafts.extend(
                {"id": record.id, "english_reference": translation.strip()}
                for record, translation in zip(batch, translations, strict=True)
            )
    write_drafts(drafts, Path(output_path), model_name)
    print(f"machine_drafts={len(drafts)} output={output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create human-review-required English drafts from Spanish references")
    parser.add_argument("--candidates", default="data/manifests/candidates.jsonl")
    parser.add_argument("--output", default="data/manifests_en/english_machine_drafts.tsv")
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    arguments = parser.parse_args()
    translate_spanish_references(
        arguments.candidates,
        arguments.output,
        arguments.model,
        arguments.batch_size,
        arguments.device,
    )
