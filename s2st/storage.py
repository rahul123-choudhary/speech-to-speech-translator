from datetime import UTC, datetime
from typing import Any

from firebase_admin import auth, credentials, firestore, initialize_app, messaging
from pymongo import MongoClient

from .settings import Settings


class ResearchStore:
    """Firebase for live state/identity; Atlas for corpus, evaluation, and pilot logs."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = None
        self.firestore = None
        if settings.mongodb_uri:
            client = MongoClient(settings.mongodb_uri, appname="quechua-direct-s2st")
            self.db = client[settings.mongodb_database]
            self.db.corpus_metadata.create_index("id", unique=True)
            self.db.evaluation_runs.create_index([("run_id", 1), ("utterance_id", 1)])
            self.db.evaluation_runs.create_index([("evaluation_run_id", 1), ("reviewer_uid", 1)])
            self.db.pilot_sessions.create_index("session_id", unique=True)
        if settings.firebase_credentials_path and settings.firebase_credentials_path.exists():
            try:
                initialize_app(credentials.Certificate(str(settings.firebase_credentials_path)))
            except ValueError:  # Firebase was initialized by another application component.
                pass
            self.firestore = firestore.client()

    def verify_token(self, token: str) -> dict[str, Any]:
        return auth.verify_id_token(token)

    def create_session(
        self,
        session_id: str,
        uid: str,
        consented: bool,
        target_language: str,
        notification_token: str | None = None,
    ) -> None:
        record = {
            "session_id": session_id,
            "uid": uid,
            "consented": consented,
            "target_language": target_language,
            "notification_token": notification_token,
            "status": "created",
            "created_at": datetime.now(UTC),
        }
        if self.firestore:
            self.firestore.collection("translation_sessions").document(session_id).set(record)
        if self.db:
            self.db.pilot_sessions.update_one({"session_id": session_id}, {"$set": record}, upsert=True)

    def update_session(self, session_id: str, status: str, **details: Any) -> None:
        record = {"status": status, "updated_at": datetime.now(UTC), **details}
        if self.firestore:
            self.firestore.collection("translation_sessions").document(session_id).set(record, merge=True)
        if self.db:
            self.db.pilot_sessions.update_one({"session_id": session_id}, {"$set": record}, upsert=True)

    def session_belongs_to(self, session_id: str, uid: str) -> bool:
        if self.firestore:
            document = self.firestore.collection("translation_sessions").document(session_id).get()
            return document.exists and document.to_dict().get("uid") == uid
        if self.db:
            return self.db.pilot_sessions.count_documents({"session_id": session_id, "uid": uid}, limit=1) == 1
        return False

    def session_notification_token(self, session_id: str) -> str | None:
        if self.firestore:
            document = self.firestore.collection("translation_sessions").document(session_id).get()
            return document.to_dict().get("notification_token") if document.exists else None
        if self.db:
            record = self.db.pilot_sessions.find_one({"session_id": session_id}, {"notification_token": 1})
            return record.get("notification_token") if record else None
        return None

    def session_target_language(self, session_id: str) -> str:
        if self.firestore:
            document = self.firestore.collection("translation_sessions").document(session_id).get()
            if document.exists:
                return document.to_dict().get("target_language", "es")
        if self.db:
            record = self.db.pilot_sessions.find_one({"session_id": session_id}, {"target_language": 1})
            if record:
                return record.get("target_language", "es")
        return "es"

    def record_evaluation(self, record: dict[str, Any]) -> None:
        if self.db:
            self.db.evaluation_runs.insert_one({**record, "recorded_at": datetime.now(UTC)})

    def upsert_corpus_metadata(self, record: dict[str, Any]) -> None:
        if self.db:
            self.db.corpus_metadata.update_one({"id": record["id"]}, {"$set": record}, upsert=True)

    def notify(self, token: str, title: str, body: str, data: dict[str, str]) -> str | None:
        if not self.firestore:
            return None
        return messaging.send(messaging.Message(notification=messaging.Notification(title=title, body=body), data=data, token=token))
