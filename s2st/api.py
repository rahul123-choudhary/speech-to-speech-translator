import base64
import os
import time
import uuid

import numpy as np
import soundfile
import torch
from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from .codec import NeuralCodec
from .evaluate import load_model
from .languages import TARGET_LANGUAGES, TargetLanguage
from .settings import get_settings
from .storage import ResearchStore

app = FastAPI(title="Direct Quechua S2ST API", version="0.1.0")
settings = get_settings()
store = ResearchStore(settings)
_runtime: dict[str, tuple] = {}


def authenticated_user(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Firebase Bearer token required")
    try:
        return store.verify_token(authorization.removeprefix("Bearer "))
    except Exception as error:
        raise HTTPException(status_code=401, detail="Invalid Firebase token") from error


class CreateSession(BaseModel):
    consented_audio_processing: bool
    target_language: TargetLanguage = "es"
    notification_token: str | None = None


class HumanEvaluation(BaseModel):
    evaluation_run_id: str | None = None
    utterance_id: str
    naturalness: int
    intelligibility: int
    adequacy: int
    cultural_appropriateness: int
    comments: str | None = None


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
    return {
        "session_id": session_id,
        "target_language": request.target_language,
        "websocket": f"/v1/sessions/{session_id}/stream",
    }


@app.get("/v1/languages")
def list_target_languages() -> dict:
    """List selectable target languages and whether each direct model is deployable."""
    languages = []
    for code, metadata in TARGET_LANGUAGES.items():
        checkpoint = getattr(settings, f"s2st_checkpoint_{code}")
        ready = bool(checkpoint and checkpoint.is_file())
        languages.append(
            {
                "code": code,
                "name": metadata["name"],
                "status": "ready" if ready else "setup_required",
                "requires": None if ready else "reviewed target speech, manifests, and trained checkpoint",
            }
        )
    return {"source_language": "que", "languages": languages}


@app.post("/v1/evaluations/human")
def submit_human_evaluation(evaluation: HumanEvaluation, user: dict = Depends(authenticated_user)) -> dict:
    ratings = [evaluation.naturalness, evaluation.intelligibility, evaluation.adequacy, evaluation.cultural_appropriateness]
    if any(rating not in range(1, 6) for rating in ratings):
        raise HTTPException(status_code=422, detail="All ratings must be integers from 1 to 5")
    store.record_evaluation({"type": "human", "reviewer_uid": user["uid"], **evaluation.model_dump()})
    return {"saved": True}


def runtime(target_language: TargetLanguage) -> tuple:
    if target_language not in TARGET_LANGUAGES:
        raise ValueError(f"Unsupported target language: {target_language}")
    if target_language not in _runtime:
        checkpoint = getattr(settings, f"s2st_checkpoint_{target_language}")
        # Keep an existing Spanish-only deployment working while it migrates.
        if checkpoint is None and target_language == "es":
            checkpoint = os.environ.get("S2ST_CHECKPOINT")
        if not checkpoint:
            language = TARGET_LANGUAGES[target_language]["name"]
            raise RuntimeError(f"Set S2ST_CHECKPOINT_{target_language.upper()} to a trained {language} best.pt file")
        device = torch.device(settings.device if torch.cuda.is_available() else "cpu")
        _runtime[target_language] = (load_model(str(checkpoint), device), NeuralCodec(str(device)), device)
    return _runtime[target_language]


@app.websocket("/v1/sessions/{session_id}/stream")
async def translate_turn(websocket: WebSocket, session_id: str, token: str = Query(...)) -> None:
    try:
        user = store.verify_token(token)
        if not store.session_belongs_to(session_id, user["uid"]):
            await websocket.close(code=4403)
            return
    except Exception:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    chunks: list[bytes] = []
    received_samples = 0
    target_language = store.session_target_language(session_id)
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
                if received_samples > settings.max_utterance_seconds * 16_000:
                    await websocket.send_json({"error": "Turn must be 0–15 seconds at 16 kHz mono"})
                    chunks.clear()
                    received_samples = 0
                    continue
                chunks.append(chunk)
                continue
            if message.get("event") != "finalize":
                await websocket.send_json({"error": "Expected audio or finalize event"})
                continue
            pcm = np.frombuffer(b"".join(chunks), dtype=np.int16).astype(np.float32) / 32768.0
            if not 0 < len(pcm) <= settings.max_utterance_seconds * 16_000:
                await websocket.send_json({"error": "Turn must be 0–15 seconds at 16 kHz mono"})
                chunks.clear()
                received_samples = 0
                continue
            store.update_session(session_id, "translating", source_samples=len(pcm), target_language=target_language)
            started = time.perf_counter()
            model, codec, device = runtime(target_language)  # type: ignore[arg-type]
            source = torch.from_numpy(pcm).unsqueeze(0).to(device)
            codes = model.generate(source, torch.tensor([source.shape[1]], device=device))
            waveform = codec.decode(codes)[0].numpy()
            buffer = __import__("io").BytesIO()
            soundfile.write(buffer, waveform, 24_000, format="WAV")
            latency_ms = (time.perf_counter() - started) * 1000
            store.update_session(session_id, "completed", latency_ms=latency_ms)
            notification_token = store.session_notification_token(session_id)
            if notification_token:
                try:
                    store.notify(
                        notification_token,
                        "Translation ready",
                        f"Your Quechua-to-{TARGET_LANGUAGES[target_language]['name']} speech translation is ready.",
                        {"session_id": session_id, "target_language": target_language},
                    )
                except Exception:
                    # Notifications are optional and must never block speech delivery.
                    pass
            await websocket.send_json(
                {
                    "event": "translation",
                    "target_language": target_language,
                    "wav_base64": base64.b64encode(buffer.getvalue()).decode(),
                    "latency_ms": latency_ms,
                }
            )
            chunks.clear()
            received_samples = 0
    except WebSocketDisconnect:
        store.update_session(session_id, "disconnected")
    except Exception as error:
        store.update_session(session_id, "failed", error=str(error))
        await websocket.send_json({"error": "Translation failed"})
        await websocket.close(code=1011)
