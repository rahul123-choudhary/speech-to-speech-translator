from datetime import UTC, datetime
from typing import Any

try:
    from firebase_admin import auth, credentials, firestore, get_app, initialize_app, messaging
    _HAS_FIREBASE = True
except ImportError:
    auth, credentials, firestore, get_app, initialize_app, messaging = None, None, None, None, None, None
    _HAS_FIREBASE = False

try:
    from pymongo import MongoClient
    _HAS_MONGO = True
except ImportError:
    MongoClient = None
    _HAS_MONGO = False

from .settings import Settings


class ResearchStore:
    """Dual database tier: Firebase for live state/auth/messaging; MongoDB Atlas for corpus metadata, models, evaluations, and pilot logs."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = None
        self.firestore = None
        self.firebase_auth_ready = False
        self.memory_sessions: dict[str, dict[str, Any]] = {}
        self.memory_evaluations: list[dict[str, Any]] = []
        self.memory_human_evaluations: list[dict[str, Any]] = []
        self.memory_community_feedback: list[dict[str, Any]] = []
        self.memory_corpus: dict[str, dict[str, Any]] = {}
        self.memory_models: dict[str, dict[str, Any]] = {}
        self.memory_project_metadata: dict[str, dict[str, Any]] = {}

        if settings.mongodb_uri and _HAS_MONGO:
            try:
                client = MongoClient(
                    settings.mongodb_uri,
                    appname="oral-tradition-direct-s2st",
                    connect=False,
                    connectTimeoutMS=3_000,
                    serverSelectionTimeoutMS=3_000,
                )
                self.db = client[settings.mongodb_database]
            except Exception:
                self.db = None

        if settings.firebase_credentials_path and settings.firebase_credentials_path.exists() and _HAS_FIREBASE:
            try:
                options = {"projectId": settings.firebase_project_id} if settings.firebase_project_id else None
                try:
                    self.firebase_app = initialize_app(
                        credentials.Certificate(str(settings.firebase_credentials_path)), options=options
                    )
                except ValueError:
                    self.firebase_app = get_app()
                self.firebase_auth_ready = True
            except Exception:
                self.firebase_app = None
            if self.firebase_auth_ready:
                try:
                    # Construct the client locally; defer network access until an
                    # authenticated request actually reads or writes a document.
                    self.firestore = firestore.client(app=self.firebase_app)
                except Exception:
                    self.firestore = None
        else:
            self.firebase_app = None

    def verify_token(self, token: str) -> dict[str, Any]:
        """Verify a signed Firebase ID token, with a tightly gated local-only dev option."""
        if self.firebase_auth_ready:
            try:
                decoded = auth.verify_id_token(token)
                role = decoded.get("role", "researcher")
                if role not in {"researcher", "community_tester", "native_speaker_reviewer"}:
                    role = "researcher"
                return {
                    "uid": decoded.get("uid"),
                    "name": decoded.get("name") or decoded.get("email") or "Authenticated User",
                    "email": decoded.get("email"),
                    "role": role,
                }
            except Exception as error:
                raise ValueError("Invalid Firebase ID token") from error

        if self.settings.allow_development_auth and token in {"dev-token", "test-token"}:
            return {
                "uid": "local_developer",
                "name": "Local Developer",
                "email": "developer@localhost",
                "role": "researcher",
            }
        raise ValueError("Firebase Authentication is not configured")

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
        self.memory_sessions[session_id] = record
        if self.firestore is not None:
            try:
                self.firestore.collection("translation_sessions").document(session_id).set(record)
            except Exception:
                pass
        if self.db is not None:
            try:
                self.db.pilot_sessions.update_one({"session_id": session_id}, {"$set": record}, upsert=True)
            except Exception:
                pass

    def update_session(self, session_id: str, status: str, **details: Any) -> None:
        record = {"status": status, "updated_at": datetime.now(UTC), **details}
        if session_id in self.memory_sessions:
            self.memory_sessions[session_id].update(record)
        if self.firestore is not None:
            try:
                self.firestore.collection("translation_sessions").document(session_id).set(record, merge=True)
            except Exception:
                pass
        if self.db is not None:
            try:
                self.db.pilot_sessions.update_one({"session_id": session_id}, {"$set": record}, upsert=True)
            except Exception:
                pass

    def session_belongs_to(self, session_id: str, uid: str) -> bool:
        if session_id in self.memory_sessions:
            return self.memory_sessions[session_id].get("uid") == uid
        if self.firestore is not None:
            try:
                document = self.firestore.collection("translation_sessions").document(session_id).get()
                if document.exists:
                    return document.to_dict().get("uid") == uid
            except Exception:
                pass
        if self.db is not None:
            try:
                return self.db.pilot_sessions.count_documents({"session_id": session_id, "uid": uid}, limit=1) == 1
            except Exception:
                pass
        return False

    def session_notification_token(self, session_id: str) -> str | None:
        if session_id in self.memory_sessions:
            return self.memory_sessions[session_id].get("notification_token")
        if self.firestore is not None:
            try:
                document = self.firestore.collection("translation_sessions").document(session_id).get()
                if document.exists:
                    return document.to_dict().get("notification_token")
            except Exception:
                pass
        if self.db is not None:
            try:
                record = self.db.pilot_sessions.find_one({"session_id": session_id}, {"notification_token": 1})
                return record.get("notification_token") if record else None
            except Exception:
                pass
        return None

    def session_target_language(self, session_id: str) -> str:
        if session_id in self.memory_sessions:
            return self.memory_sessions[session_id].get("target_language", "or")
        if self.firestore is not None:
            try:
                document = self.firestore.collection("translation_sessions").document(session_id).get()
                if document.exists:
                    return document.to_dict().get("target_language", "or")
            except Exception:
                pass
        if self.db is not None:
            try:
                record = self.db.pilot_sessions.find_one({"session_id": session_id}, {"target_language": 1})
                if record:
                    return record.get("target_language", "or")
            except Exception:
                pass
        return "or"

    def record_evaluation(self, record: dict[str, Any]) -> None:
        """Record automated ASR-BLEU evaluation run into MongoDB Atlas and memory."""
        entry = {**record, "recorded_at": datetime.now(UTC)}
        self.memory_evaluations.append(entry)
        if self.db is not None:
            try:
                self.db.evaluation_runs.insert_one(entry)
            except Exception:
                pass

    def record_human_evaluation(self, record: dict[str, Any]) -> None:
        """Record multi-dimensional human rating into MongoDB Atlas."""
        entry = {**record, "recorded_at": datetime.now(UTC)}
        self.memory_human_evaluations.append(entry)
        if self.db is not None:
            try:
                self.db.human_evaluations.insert_one(entry)
            except Exception:
                pass

    def record_community_feedback(self, record: dict[str, Any]) -> None:
        """Record community validation feedback and cultural appropriateness review into Atlas."""
        entry = {**record, "recorded_at": datetime.now(UTC)}
        self.memory_community_feedback.append(entry)
        if self.db is not None:
            try:
                self.db.community_feedback.insert_one(entry)
            except Exception:
                pass

    def upsert_corpus_metadata(self, record: dict[str, Any]) -> None:
        """Save aligned utterance pair and provenance metadata in MongoDB Atlas."""
        self.memory_corpus[record["id"]] = record
        if self.db is not None:
            try:
                self.db.corpus_metadata.update_one({"id": record["id"]}, {"$set": record}, upsert=True)
            except Exception:
                pass

    def upsert_model_metadata(self, record: dict[str, Any]) -> None:
        """Save LoRA adapter configuration, foundation base model, and checkpoint stats."""
        model_id = record.get("model_id", "default_model")
        self.memory_models[model_id] = record
        if self.db is not None:
            try:
                self.db.model_metadata.update_one({"model_id": model_id}, {"$set": record}, upsert=True)
            except Exception:
                pass

    def upsert_project_metadata(self, record: dict[str, Any]) -> None:
        """Save the project's own configuration/status document."""
        project_id = record["project_id"]
        self.memory_project_metadata[project_id] = record
        if self.db is not None:
            try:
                self.db.project_metadata.update_one({"project_id": project_id}, {"$set": record}, upsert=True)
            except Exception:
                pass

    def notify(self, token: str, title: str, body: str, data: dict[str, str]) -> str | None:
        """Dispatch push alert via Firebase Cloud Messaging (FCM)."""
        if self.firestore is None:
            return None
        try:
            return messaging.send(
                messaging.Message(
                    notification=messaging.Notification(title=title, body=body),
                    data=data,
                    token=token,
                )
            )
        except Exception:
            return None

    def get_status(self) -> dict[str, Any]:
        """Return connectivity health and object counts for Firebase & MongoDB Atlas."""
        mongo_connected = self.db is not None
        firestore_connected = self.firestore is not None

        corpus_count = len(self.memory_corpus)
        eval_count = len(self.memory_evaluations)
        human_count = len(self.memory_human_evaluations)
        feedback_count = len(self.memory_community_feedback)
        sessions_count = len(self.memory_sessions)
        project_metadata_count = len(self.memory_project_metadata)

        if mongo_connected:
            try:
                corpus_count = self.db.corpus_metadata.count_documents({})
                eval_count = self.db.evaluation_runs.count_documents({})
                human_count = self.db.human_evaluations.count_documents({})
                feedback_count = self.db.community_feedback.count_documents({})
                sessions_count = self.db.pilot_sessions.count_documents({})
                project_metadata_count = self.db.project_metadata.count_documents({})
            except Exception:
                mongo_connected = False
                self.db = None

        return {
            "firebase": {
                "auth": "ready" if self.firebase_auth_ready else "not_configured",
                "firestore_live_sync": "active" if firestore_connected else "in_memory",
                "fcm_messaging": "not_integrated",
                "project_id": self.settings.firebase_project_id,
            },
            "mongodb_atlas": {
                "connected": mongo_connected,
                "database": self.settings.mongodb_database,
                "data_location": "mongodb_atlas" if mongo_connected else "in_memory_only",
                "persistent": mongo_connected,
                "notice": None if mongo_connected else "MongoDB Atlas is not connected. Data is held in server memory and is lost when the app stops.",
                "project_metadata_records": project_metadata_count,
                "corpus_metadata_records": corpus_count,
                "evaluation_runs_count": eval_count,
                "human_evaluations_count": human_count,
                "community_feedback_count": feedback_count,
                "pilot_sessions_count": sessions_count,
            },
        }
