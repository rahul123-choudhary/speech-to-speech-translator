"""Upsert this project's configuration/status document into MongoDB Atlas."""

from datetime import UTC, datetime
from pathlib import Path

import yaml
from pymongo import MongoClient

from s2st.settings import get_settings


PROJECT_ID = "yoruba-s2st"


def main() -> None:
    settings = get_settings()
    if not settings.mongodb_uri:
        raise SystemExit("MONGODB_URI is not configured in .env")

    config_path = Path("configs/yor_en_s2st.yaml")
    training_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    record = {
        "project_id": PROJECT_ID,
        "project_name": "Yorùbá to English Speech Translation",
        "source_language": training_config["source_language"],
        "target_language": training_config["target_language"],
        "training_config": training_config,
        "project_status": "configuration_only_no_trainable_corpus_or_checkpoint",
        "local_data_inventory": {
            "user_owned_audio_files": 0,
            "aligned_speech_pair_manifests": 0,
            "trained_checkpoints": 0,
            "human_review_records": 0,
            "iwslt_candidate_manifest_present": Path(
                "data/iwslt2026_yoruba/processed/candidates.jsonl"
            ).is_file(),
            "iwslt_native_review_template_present": Path(
                "data/iwslt2026_yoruba/processed/native_review.csv"
            ).is_file(),
        },
        "synced_at": datetime.now(UTC),
    }

    try:
        with MongoClient(settings.mongodb_uri, appname="oral-tradition-s2st-metadata-sync") as client:
            client.admin.command("ping")
            collection = client[settings.mongodb_database].project_metadata
            collection.create_index("project_id", unique=True)
            collection.update_one({"project_id": PROJECT_ID}, {"$set": record}, upsert=True)
            print(
                "MongoDB connection verified; project configuration synced; "
                f"project_metadata_records={collection.count_documents({})}"
            )
    except Exception:
        raise SystemExit("MongoDB sync failed. Credentials were not printed; check Atlas access and .env.") from None


if __name__ == "__main__":
    main()
