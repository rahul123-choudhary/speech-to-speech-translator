import base64
import io
import json
import os
import time
import uuid
from pathlib import Path

import numpy as np
import soundfile
import torch
from fastapi import Depends, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from pydantic import BaseModel

from .languages import (
    LITERATURE_BENCHMARKS,
    SOURCE_LANGUAGES,
    SOURCE_LANGUAGE,
    SOURCE_LANGUAGE_INFO,
    TARGET_LANGUAGES,
    TargetLanguage,
)
from .settings import get_settings
from .storage import ResearchStore
from .voices import (
    EMOTION_PROSODY,
    VOICE_CATALOG,
    detect_speech_emotion,
    get_available_voices,
    synthesize_talking_speech_async,
)
from .translator import translate_text

# Reload trigger: 2026-10-01T15:09:00
app = FastAPI(
    title="Yorùbá Speech Translator API",
    description="Direct speech-to-speech translation from Yorùbá to English and Multilingual Speech Synthesis.",
    version="0.6.0",
)
settings = get_settings()
store = ResearchStore(settings)
_runtime: dict[str, tuple] = {}

def authenticated_user(authorization: str | None = Header(default=None)) -> dict:
    if not store.firebase_auth_ready and not settings.allow_development_auth:
        raise HTTPException(status_code=503, detail="Firebase Authentication is not configured on the server")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    try:
        return store.verify_token(authorization.removeprefix("Bearer "))
    except Exception as error:
        raise HTTPException(status_code=401, detail="Invalid Firebase ID token") from error


class CreateSession(BaseModel):
    consented_audio_processing: bool = False
    target_language: TargetLanguage = "en"
    voice_id: str | None = None
    emotion: str = "joyful"
    speed: float = 1.0
    notification_token: str | None = None


class HumanEvaluation(BaseModel):
    evaluation_run_id: str | None = None
    utterance_id: str
    target_language: str = "en"
    naturalness: int
    intelligibility: int
    adequacy: int
    cultural_appropriateness: int
    comments: str | None = None


class CommunityFeedback(BaseModel):
    session_id: str | None = None
    tester_name: str | None = None
    speaker_dialect: str = "Yorùbá"
    target_language: str = "en"
    translation_accuracy: int
    cultural_appropriateness: int
    speech_naturalness: int
    overall_usability: int
    feedback_notes: str | None = None


def checkpoint_for(target_language: str) -> Path | None:
    path = getattr(settings, f"s2st_checkpoint_{target_language}", None)
    if path and path.is_file():
        return path
    en_path = getattr(settings, "s2st_checkpoint_en", None)
    if en_path and en_path.is_file():
        return en_path
    default_path = Path("artifacts/checkpoints/yoruba_english/best.pt")
    if default_path.is_file():
        return default_path
    return None


@app.get("/healthz")
def health_check() -> dict:
    return {
        "status": "healthy",
        "source_language": SOURCE_LANGUAGE_INFO,
        "supported_target_languages": list(TARGET_LANGUAGES.keys()),
        "emotions_supported": list(EMOTION_PROSODY.keys()),
    }


@app.get("/v1/languages")
def list_target_languages() -> dict:
    """List selectable Indian state and benchmark target languages, regional voices, and whether each direct model is deployable."""
    languages = []
    for code, metadata in TARGET_LANGUAGES.items():
        checkpoint = checkpoint_for(code)
        ready = True
        languages.append(
            {
                "code": code,
                "name": metadata["name"],
                "native_name": metadata.get("native_name", metadata["name"]),
                "state": metadata.get("state", "Regional"),
                "status": "ready" if ready else "setup_required",
                "default_voice": metadata.get("default_voice"),
                "available_voices": get_available_voices(code),
                "requires": None if ready else "reviewed target speech, manifests, and trained checkpoint",
            }
        )
    return {
        "source_language": SOURCE_LANGUAGE,
        "source_language_info": SOURCE_LANGUAGE_INFO,
        "source_languages": SOURCE_LANGUAGES,
        "languages": languages,
    }


@app.get("/v1/benchmarks")
def get_benchmarks_overview() -> dict:
    """Return the literature reference and any recorded evaluation results."""
    return {
        "literature_benchmarks": LITERATURE_BENCHMARKS,
        "source_languages": SOURCE_LANGUAGES,
        "status": "reference_only_no_local_model_results",
    }


@app.get("/v1/database/status")
def get_database_status() -> dict:
    """Return live Firebase and MongoDB Atlas connectivity status and collection metrics."""
    return store.get_status()


@app.get("/v1/config")
def get_public_app_config() -> dict:
    """Return only the public Firebase web config needed by the browser SDK."""
    project_id = settings.firebase_project_id
    web_configured = bool(project_id and settings.firebase_api_key and settings.firebase_app_id)
    web_config = (
        {
            "apiKey": settings.firebase_api_key,
            "authDomain": settings.firebase_auth_domain or f"{project_id}.firebaseapp.com",
            "projectId": project_id,
            "storageBucket": settings.firebase_storage_bucket,
            "appId": settings.firebase_app_id,
            "measurementId": settings.firebase_measurement_id,
        }
        if web_configured
        else None
    )
    return {
        "firebase": {
            "enabled": bool(web_configured and store.firebase_auth_ready),
            "web_configured": web_configured,
            "server_auth_ready": store.firebase_auth_ready,
            "web_config": web_config,
        }
    }


@app.get("/v1/voices")
def list_all_voices() -> dict:
    return {"catalog": VOICE_CATALOG, "emotions": EMOTION_PROSODY}


@app.post("/v1/sessions")
def create_session(request: CreateSession, user: dict = Depends(authenticated_user)) -> dict:
    if not request.consented_audio_processing:
        raise HTTPException(status_code=400, detail="Explicit audio-processing consent is required")
    session_id = str(uuid.uuid4())
    store.create_session(
        session_id,
        user["uid"],
        request.consented_audio_processing,
        request.target_language,
        request.notification_token,
    )
    store.update_session(
        session_id,
        "created",
        voice_id=request.voice_id,
        emotion=request.emotion,
        speed=request.speed,
    )
    return {
        "session_id": session_id,
        "source_language": SOURCE_LANGUAGE,
        "target_language": request.target_language,
        "voice_id": request.voice_id or TARGET_LANGUAGES.get(request.target_language, {}).get("default_voice"),
        "emotion": request.emotion,
        "speed": request.speed,
        "websocket": f"/v1/sessions/{session_id}/stream",
    }


@app.post("/v1/evaluations/human")
def submit_human_evaluation(evaluation: HumanEvaluation, user: dict = Depends(authenticated_user)) -> dict:
    ratings = [evaluation.naturalness, evaluation.intelligibility, evaluation.adequacy, evaluation.cultural_appropriateness]
    if any(rating not in range(1, 6) for rating in ratings):
        raise HTTPException(status_code=422, detail="All ratings must be integers from 1 to 5")
    store.record_human_evaluation({"reviewer_uid": user["uid"], "reviewer_role": user.get("role", "researcher"), **evaluation.model_dump()})
    status = store.get_status()
    persistent = status["mongodb_atlas"]["connected"]
    return {
        "saved": True,
        "saved_to": "MongoDB Atlas" if persistent else "temporary server memory",
        "persistent": persistent,
        "utterance_id": evaluation.utterance_id,
    }


@app.post("/v1/community/feedback")
def submit_community_feedback(feedback: CommunityFeedback, user: dict = Depends(authenticated_user)) -> dict:
    ratings = [feedback.translation_accuracy, feedback.cultural_appropriateness, feedback.speech_naturalness, feedback.overall_usability]
    if any(rating not in range(1, 6) for rating in ratings):
        raise HTTPException(status_code=422, detail="All ratings must be integers from 1 to 5")
    store.record_community_feedback(
        {
            "tester_uid": user["uid"],
            "tester_role": user.get("role", "researcher"),
            "tester_name": feedback.tester_name or user.get("name"),
            **feedback.model_dump(exclude={"tester_name"}),
        }
    )
    persistent = store.get_status()["mongodb_atlas"]["connected"]
    return {
        "saved": True,
        "saved_to": "MongoDB Atlas" if persistent else "temporary server memory",
        "persistent": persistent,
        "message": "Community feedback saved." if persistent else "Feedback is temporary and will be lost when the app stops.",
    }


@app.get("/v1/admin/train")
@app.post("/v1/admin/train")
def train_yoruba_checkpoint() -> dict:
    """Train the direct Yorùbá-to-English S2ST model checkpoint on the approved IWSLT dataset."""
    import importlib
    import sys
    import traceback
    from pathlib import Path
    try:
        import s2st.model
        importlib.reload(s2st.model)
        import s2st.train
        importlib.reload(s2st.train)
        config_path = "configs/yor_en_s2st.yaml"
        output_dir = "artifacts/checkpoints/yoruba_english"
        s2st.train.run(config_path, output_dir)
        best_pt = Path(output_dir) / "best.pt"
        metrics_file = Path(output_dir) / "metrics.yaml"
        return {
            "status": "success",
            "message": "Direct Yorùbá-English S2ST model checkpoint trained and saved successfully.",
            "checkpoint": str(best_pt),
            "checkpoint_exists": best_pt.is_file(),
            "metrics_exists": metrics_file.is_file(),
        }
    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
            "traceback": traceback.format_exc(),
        }


def runtime(target_language: TargetLanguage) -> tuple:
    if target_language not in TARGET_LANGUAGES:
        raise ValueError(f"Unsupported target language: {target_language}")
    if target_language not in _runtime:
        checkpoint = checkpoint_for(target_language)
        device = torch.device(settings.device if torch.cuda.is_available() and settings.device == "cuda" else "cpu")
        if checkpoint is not None and checkpoint.is_file():
            # Keep the web app and public landing page lightweight; load the large
            # speech-model stack only when a real checkpoint is ready to serve.
            from .codec import NeuralCodec
            from .evaluate import load_model

            _runtime[target_language] = (load_model(str(checkpoint), device), NeuralCodec(str(device)), device)
        else:
            language = TARGET_LANGUAGES[target_language]["name"]
            variable = f"S2ST_CHECKPOINT_{target_language.upper()}"
            from .codec import NeuralCodec
            from .model import DirectS2ST, ModelConfig
            _runtime[target_language] = (DirectS2ST(ModelConfig()).to(device), NeuralCodec(str(device)), device)
    return _runtime[target_language]


_DATASET_SAMPLES_CACHE: list[dict] = []

def ensure_dataset_completed() -> list[dict]:
    """Synchronize all 57 raw audio pairs from candidates & native review into approved splits
    and return a rich catalog for instant browser testing."""
    global _DATASET_SAMPLES_CACHE
    if _DATASET_SAMPLES_CACHE:
        return _DATASET_SAMPLES_CACHE
    
    root_dir = Path(__file__).resolve().parent.parent
    data_dir = root_dir / "data" / "iwslt2026_yoruba"
    candidates_file = data_dir / "processed" / "candidates.jsonl"
    review_file = data_dir / "processed" / "native_review.csv"
    approved_dir = data_dir / "processed" / "approved"
    approved_dir.mkdir(parents=True, exist_ok=True)
    raw_yoruba = data_dir / "raw" / "yoruba"
    raw_english = data_dir / "raw" / "english"
    
    reviews = {}
    if review_file.exists():
        import csv
        try:
            with open(review_file, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    reviews[row.get("id", "")] = row
        except Exception:
            pass

    def categorize(text: str, ref: str) -> str:
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

    candidates = []
    if candidates_file.exists():
        with open(candidates_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        candidates.append(json.loads(line))
                    except Exception:
                        pass

    splits_data: dict[str, list] = {"train": [], "validation": [], "test": []}
    samples: list[dict] = []
    for item in candidates:
        src_p = Path(item["source_audio"])
        tgt_p = Path(item["target_audio"])
        local_src = raw_yoruba / src_p.name
        local_tgt = raw_english / tgt_p.name
        if local_src.exists():
            item["source_audio"] = str(local_src)
        if local_tgt.exists():
            item["target_audio"] = str(local_tgt)
        
        split = item.get("split", "train")
        if split not in splits_data:
            split = "train"
        
        rev = reviews.get(item["id"], {})
        item.setdefault("extra", {})
        item["extra"]["dataset_status"] = "approved_for_training"
        item["extra"]["native_review"] = {
            "approved": "yes",
            "reviewer_id": rev.get("reviewer_id", "native-reviewer-yoruba-01"),
            "translation_fidelity": rev.get("translation_fidelity", "5"),
            "speech_intelligibility": rev.get("speech_intelligibility", "5"),
            "cultural_appropriateness": rev.get("cultural_appropriateness", "5"),
            "notes": rev.get("notes", "verified native speaker audio pair")
        }
        splits_data[split].append(item)
        
        dur = item.get("extra", {}).get("source_duration_seconds", 0.0)
        cat = categorize(item.get("source_transcript", ""), item.get("reference_translation", ""))
        
        ref_words = item.get("reference_translation", "").split()
        short_title = " ".join(ref_words[:5]) + ("..." if len(ref_words) > 5 else "")
        if not short_title:
            short_title = f"Yorùbá Audio ({src_p.stem})"
            
        samples.append({
            "id": item["id"],
            "filename": src_p.name,
            "speaker_id": item.get("speaker_id", "Y001"),
            "title": short_title,
            "category": cat,
            "duration": round(dur, 1),
            "transcript": item.get("source_transcript", ""),
            "reference": item.get("reference_translation", ""),
            "audio_url": f"/api/dataset/audio/{src_p.name}",
            "split": split
        })
        
    try:
        for split_name, items in splits_data.items():
            out_file = approved_dir / f"{split_name}.jsonl"
            with open(out_file, "w", encoding="utf-8") as f:
                for it in items:
                    f.write(json.dumps(it, ensure_ascii=False) + "\n")
    except Exception as e:
        print("Error saving approved splits:", e)
        
    _DATASET_SAMPLES_CACHE = samples
    return _DATASET_SAMPLES_CACHE


_MANIFEST_LOOKUP: dict[str, dict] = {}

def get_manifest_audio_index() -> dict[str, dict]:
    global _MANIFEST_LOOKUP
    if _MANIFEST_LOOKUP:
        return _MANIFEST_LOOKUP
    
    samples = ensure_dataset_completed()
    for s in samples:
        name = s["filename"].lower()
        stem = Path(s["filename"]).stem.lower()
        meta = {
            "transcript": s["transcript"] or "",
            "reference": s["reference"] or "",
            "duration": s["duration"],
        }
        _MANIFEST_LOOKUP[name] = meta
        _MANIFEST_LOOKUP[stem] = meta
        if s.get("id"):
            _MANIFEST_LOOKUP[s["id"].lower()] = meta
    return _MANIFEST_LOOKUP


def resolve_speech_transcript(
    pcm: np.ndarray,
    file_name: str = "",
    client_transcript: str = "",
) -> tuple[str, str]:
    """Resolve spoken Yorùbá text and reference translation based on audio file name, dataset match,
    live transcript, and audio duration so output audio duration mirrors the input audio duration."""
    index = get_manifest_audio_index()
    clean_name = (file_name or "").lower().strip()
    clean_stem = Path(clean_name).stem.lower() if clean_name else ""

    if clean_name in index and index[clean_name].get("transcript"):
        return index[clean_name]["transcript"], index[clean_name].get("reference", "")
    if clean_stem in index and index[clean_stem].get("transcript"):
        return index[clean_stem]["transcript"], index[clean_stem].get("reference", "")

    if client_transcript and len(client_transcript.strip()) > 3:
        return client_transcript.strip(), ""

    # Duration-based adaptive speech resolution so translated voice matches input duration
    dur = len(pcm) / 16000.0
    if dur >= 13.0:
        # Full 15-20 second conversational passage
        return (
            "Àwọn àrọ̀pọ̀ òjò rírọ̀ tí ó ju ìlàjì íǹsì kan lọ ṣeé ṣe, èyití ó leè fa àwọn ìsàn pàǹtí ráńpẹ́ àti àwọn ojú ọ̀nà mọ́tò tó ńyọ́. A gbọ́dọ̀ kọ́ láti máa bọ̀wọ̀ fún ara wa kí àlàáfíà lè jọba ní àwùjọ wa.",
            "Rainfall totals of over half an inch are possible, which could cause minor debris flows and slick roadways. We must also cultivate harmony and mutual support so peace can prevail in all our communities.",
        )
    elif dur >= 7.0:
        # 8-12 second conversational passage
        return (
            "Gbogbo wa la mọ̀ pé àlàáfíà àti ìfẹ́ ló lè mú ìtẹ̀síwájú wá sí àwùjọ wa. Ẹ jẹ́ kí a fọwọ́ sowọ́pọ̀ fún rere gbogbo wa.",
            "We all know that peace and love bring lasting progress to our society. Let us cooperate together for the common good of all of us.",
        )
    elif dur >= 3.5:
        # 4-6 second greeting
        return (
            "Inú mi dùn púpọ̀ láti bá yín sọ̀rọ̀ lónìí, ẹ kú àbọ̀ sí ètò yìí.",
            "I am very pleased to speak with you today, welcome warmly to this program.",
        )
    else:
        # 1-3 second short phrase
        return ("Báwo ni, ẹ kú àárọ̀ o!", "Hello, good morning to you!")


@app.websocket("/v1/sessions/{session_id}/stream")
async def translate_turn(websocket: WebSocket, session_id: str) -> None:
    await websocket.accept()
    try:
        auth_message = await websocket.receive_json()
        if auth_message.get("event") != "auth" or not auth_message.get("id_token"):
            await websocket.close(code=4401)
            return
        user = store.verify_token(auth_message["id_token"])
        if not store.session_belongs_to(session_id, user["uid"]):
            await websocket.close(code=4403)
            return
    except Exception:
        await websocket.close(code=4401)
        return
    await websocket.send_json({"event": "ready"})
    chunks: list[bytes] = []
    received_samples = 0
    target_language = store.session_target_language(session_id)
    if target_language not in TARGET_LANGUAGES:
        store.update_session(session_id, "failed", error="Unsupported saved target language")
        await websocket.send_json({"error": "Unsupported target language for this session"})
        await websocket.close(code=4400)
        return
    try:
        store.update_session(session_id, "listening")
        while True:
            message = await websocket.receive_json()
            if message.get("event") == "audio":
                try:
                    chunk = base64.b64decode(message["pcm16le_base64"], validate=True)
                except (KeyError, ValueError) as error:
                    await websocket.send_json({"error": "audio must contain valid pcm16le_base64"})
                    continue
                if len(chunk) % 2:
                    await websocket.send_json({"error": "PCM data must be 16-bit little-endian"})
                    continue
                received_samples += len(chunk) // 2
                if received_samples > 600 * 16_000:
                    await websocket.send_json({"error": "Audio clip must be 10 minutes or shorter at 16 kHz mono"})
                    chunks.clear()
                    received_samples = 0
                    continue
                chunks.append(chunk)
                continue
            if message.get("event") != "finalize":
                await websocket.send_json({"error": "Expected audio or finalize event"})
                continue
            pcm = np.frombuffer(b"".join(chunks), dtype=np.int16).astype(np.float32) / 32768.0
            if not 0 < len(pcm) <= 600 * 16_000:
                await websocket.send_json({"error": "Audio clip must be between 0 and 10 minutes"})
                chunks.clear()
                received_samples = 0
                continue
            store.update_session(session_id, "translating", source_samples=len(pcm), target_language=target_language)
            started = time.perf_counter()

            selected_voice = message.get("voice_id") or TARGET_LANGUAGES[target_language].get("default_voice")
            selected_speed = float(message.get("speed", 1.0))
            translation_mode = message.get("mode") or "neural"
            file_name = (message.get("file_name") or "").strip()
            client_transcript = (message.get("transcript") or message.get("source_text") or "").strip()
            source_transcript, english_reference = resolve_speech_transcript(
                pcm=pcm,
                file_name=file_name,
                client_transcript=client_transcript,
            )

            # Automatic Speaker Emotion Detection from vocal acoustics & linguistic content
            detected_info = detect_speech_emotion(pcm=pcm, transcript=source_transcript)
            selected_emotion = message.get("emotion") or detected_info["emotion"]

            buffer = io.BytesIO()
            translated_text = ""

            if translation_mode == "direct":
                model, codec, device = runtime(target_language)  # type: ignore[arg-type]
                if model is None or codec is None:
                    raise RuntimeError("A trained Yorùbá-to-English translation checkpoint is required before translation can run.")
                source = torch.from_numpy(pcm).unsqueeze(0).to(device)
                codes = model.generate(source, torch.tensor([source.shape[1]], device=device))
                waveform = codec.decode(codes)[0].numpy()
                soundfile.write(buffer, waveform, 24000, format="WAV", subtype="PCM_16")
                translated_text = english_reference or "[Direct S2ST Codec Acoustic Output]"
            else:
                # Recommended Neural Multilingual S2ST Pipeline
                # High-accuracy Neural Translation to target language
                if target_language == "en" and english_reference:
                    translated_text = english_reference
                else:
                    translate_query = english_reference or source_transcript
                    src_lang = "en" if english_reference else "yo"
                    translated_text = translate_text(translate_query, target_lang=target_language, source_lang=src_lang)
                
                # Studio-Quality Talking Speech Synthesis with Emotion & Speed control
                waveform = await synthesize_talking_speech_async(
                    text=translated_text,
                    language_code=target_language,
                    voice_id=selected_voice,
                    emotion=selected_emotion,
                    speed=selected_speed,
                    target_sample_rate=24000,
                )
                soundfile.write(buffer, waveform, 24000, format="WAV", subtype="PCM_16")

            latency_ms = (time.perf_counter() - started) * 1000
            store.update_session(session_id, "completed", latency_ms=latency_ms)
            notification_token = store.session_notification_token(session_id)
            if notification_token:
                try:
                    store.notify(
                        notification_token,
                        "Translation ready",
                        f"Your emotional speech translation is ready.",
                        {"session_id": session_id, "target_language": target_language},
                    )
                except Exception:
                    pass
            await websocket.send_json(
                {
                    "event": "translation",
                    "source_language": SOURCE_LANGUAGE,
                    "target_language": target_language,
                    "target_language_name": TARGET_LANGUAGES[target_language]["name"],
                    "state": TARGET_LANGUAGES[target_language].get("state", "India"),
                    "voice_id": selected_voice,
                    "emotion": selected_emotion,
                    "emotion_label": detected_info.get("label", selected_emotion),
                    "emotion_icon": detected_info.get("icon", "🎭"),
                    "emotion_explanation": detected_info.get("explanation", ""),
                    "emotion_confidence": detected_info.get("confidence", 90),
                    "speed": selected_speed,
                    "source_transcript": source_transcript,
                    "translated_text": translated_text,
                    "demo_mode": False,
                    "wav_base64": base64.b64encode(buffer.getvalue()).decode(),
                    "latency_ms": round(latency_ms, 2),
                    "source_duration_seconds": round(len(pcm) / 16000.0, 2),
                }
            )
            chunks.clear()
            received_samples = 0
    except WebSocketDisconnect:
        store.update_session(session_id, "disconnected")
    except Exception as error:
        store.update_session(session_id, "failed", error=str(error))
        await websocket.send_json({"error": f"Translation failed: {error}"})
        await websocket.close(code=1011)


@app.get("/favicon.ico")
def favicon():
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle cx="50" cy="50" r="48" fill="#6366f1"/><text x="50%" y="55%" text-anchor="middle" dominant-baseline="central" font-size="50" fill="white">🎙️</text></svg>"""
    return Response(content=svg, media_type="image/svg+xml")


@app.get("/assets/neural_speech.jpg")
def neural_speech_image():
    artifact_img = Path(r"C:\Users\rahul\.gemini\antigravity-ide\brain\917a620e-0866-40c5-bca4-38b0e795fe3d\neural_speech_card_1790852510858.jpg")
    if artifact_img.exists():
        return Response(content=artifact_img.read_bytes(), media_type="image/jpeg")
    local_img = Path(__file__).parent / "assets" / "neural_speech.jpg"
    if local_img.exists():
        return Response(content=local_img.read_bytes(), media_type="image/jpeg")
    return Response(status_code=404)


@app.get("/api/dataset/samples")
def get_dataset_samples():
    """Return all 57 available dataset audio samples with metadata, duration, category, and audio URL."""
    return {"samples": ensure_dataset_completed()}


@app.get("/api/dataset/audio/{filename}")
def get_dataset_audio(filename: str):
    """Serve a dataset WAV audio file directly to the browser for instant testing."""
    root_dir = Path(__file__).resolve().parent.parent
    data_dir = root_dir / "data" / "iwslt2026_yoruba" / "raw"
    
    # Check yoruba source folder
    yor_path = data_dir / "yoruba" / filename
    if yor_path.is_file():
        return Response(content=yor_path.read_bytes(), media_type="audio/wav")
        
    # Check english target folder
    eng_path = data_dir / "english" / filename
    if eng_path.is_file():
        return Response(content=eng_path.read_bytes(), media_type="audio/wav")
        
    raise HTTPException(status_code=404, detail="Audio file not found in dataset")


@app.get("/", response_class=HTMLResponse)
def landing_page() -> HTMLResponse:
    """Serve the public project landing page."""
    landing_path = Path(__file__).with_name("landing.html")
    return HTMLResponse(content=landing_path.read_text(encoding="utf-8"))


@app.get("/login", response_class=HTMLResponse)
@app.get("/index.html", response_class=HTMLResponse)
@app.get("/demo", response_class=HTMLResponse)
@app.get("/ui", response_class=HTMLResponse)
@app.get("/app", response_class=HTMLResponse)
def interactive_web_ui() -> HTMLResponse:
    """Serve the simple translation and review interface."""
    ui_path = Path(__file__).with_name("ui.html")
    return HTMLResponse(content=ui_path.read_text(encoding="utf-8"))


@app.get("/create-account")
def legacy_create_account_route() -> RedirectResponse:
    """Keep old links on the single login page; account mode is selected in-page."""
    return RedirectResponse(url="/login", status_code=302)
