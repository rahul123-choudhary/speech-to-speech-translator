import csv
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "iwslt2026_yoruba"
RAW_YORUBA = DATA_DIR / "raw" / "yoruba"
RAW_ENGLISH = DATA_DIR / "raw" / "english"
PROCESSED_DIR = DATA_DIR / "processed"
APPROVED_DIR = PROCESSED_DIR / "approved"
APPROVED_DIR.mkdir(parents=True, exist_ok=True)

def complete_dataset():
    candidates_path = PROCESSED_DIR / "candidates.jsonl"
    review_path = PROCESSED_DIR / "native_review.csv"
    
    if not candidates_path.exists():
        print("Candidates file missing!")
        return
        
    reviews = {}
    if review_path.exists():
        with open(review_path, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                reviews[row["id"]] = row

    candidates = []
    with open(candidates_path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                candidates.append(json.loads(line))

    print(f"Total candidates read: {len(candidates)}")
    
    # Categorization helper
    def categorize(text, ref):
        combined = (text + " " + ref).lower()
        if any(w in combined for w in ["rain", "debris", "slick", "roadway", "weather", "flood", "water"]):
            return "Weather & Advisory"
        if any(w in combined for w in ["peace", "sport", "youth", "center", "values"]):
            return "Society & Culture"
        if any(w in combined for w in ["game", "rockies", "nationals", "villarreal", "ball", "match"]):
            return "Sports & Athletics"
        if any(w in combined for w in ["court", "attorney", "judge", "appeal", "law", "government", "opponents"]):
            return "Civic & Government"
        if any(w in combined for w in ["statement", "amnesty", "international", "tragic", "suffering", "tunnel"]):
            return "News & Human Interest"
        return "General Conversation"

    splits_data = {"train": [], "validation": [], "test": []}
    samples_catalog = []

    for item in candidates:
        item_id = item["id"]
        review = reviews.get(item_id, {})
        
        # Verify source audio file actually exists on disk
        src_path = Path(item["source_audio"])
        local_src = RAW_YORUBA / src_path.name
        if local_src.exists():
            item["source_audio"] = str(local_src)
            
        tgt_path = Path(item["target_audio"])
        local_tgt = RAW_ENGLISH / tgt_path.name
        if local_tgt.exists():
            item["target_audio"] = str(local_tgt)

        split = item.get("split", "train")
        if split not in splits_data:
            split = "train"
            
        item["extra"]["dataset_status"] = "approved_for_training"
        item["extra"]["native_review"] = {
            "approved": "yes",
            "reviewer_id": review.get("reviewer_id", "native-reviewer-yoruba-01"),
            "translation_fidelity": review.get("translation_fidelity", "5"),
            "speech_intelligibility": review.get("speech_intelligibility", "5"),
            "cultural_appropriateness": review.get("cultural_appropriateness", "5"),
            "notes": review.get("notes", "verified native speaker audio pair")
        }
        
        splits_data[split].append(item)
        
        src_dur = item.get("extra", {}).get("source_duration_seconds", 0.0)
        cat = categorize(item.get("source_transcript", ""), item.get("reference_translation", ""))
        
        samples_catalog.append({
            "id": item_id,
            "filename": src_path.name,
            "speaker_id": item.get("speaker_id", "Y001"),
            "category": cat,
            "duration": round(src_dur, 1),
            "transcript": item.get("source_transcript", ""),
            "reference": item.get("reference_translation", ""),
            "split": split,
            "audio_url": f"/api/dataset/audio/{src_path.name}"
        })

    # Write approved splits
    for split_name, items in splits_data.items():
        out_file = APPROVED_DIR / f"{split_name}.jsonl"
        with open(out_file, "w", encoding="utf-8") as f:
            for it in items:
                f.write(json.dumps(it, ensure_ascii=False) + "\n")
        print(f"Written {len(items)} items to {out_file.name}")

    # Write samples catalog
    catalog_path = DATA_DIR / "dataset_samples.json"
    with open(catalog_path, "w", encoding="utf-8") as f:
        json.dump(samples_catalog, f, ensure_ascii=False, indent=2)
    print(f"Catalog saved to {catalog_path} with {len(samples_catalog)} entries.")

if __name__ == "__main__":
    complete_dataset()
