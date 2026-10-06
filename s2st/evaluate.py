import argparse
import hashlib
import json
import time
import uuid
from pathlib import Path

import sacrebleu
import soundfile
import torch

from .codec import NeuralCodec
from .data import load_mono
from .languages import TARGET_LANGUAGES
from .manifest import read_manifest
from .model import DirectS2ST, ModelConfig
from .settings import get_settings
from .storage import ResearchStore


def load_model(checkpoint_path: str, device: torch.device) -> DirectS2ST:
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
    model = DirectS2ST(ModelConfig(**checkpoint["config"])).to(device)
    model.load_state_dict(checkpoint["state_dict"])
    return model.eval()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(
    checkpoint_path: str,
    manifest_path: str,
    output_dir: str = "artifacts/evaluation",
    target_language: str | None = None,
) -> dict:
    records = list(read_manifest(manifest_path))
    if not records:
        raise ValueError(f"No test records in {manifest_path}")
    unauthorized = [
        record.id
        for record in records
        if record.extra.get("dataset_status") != "approved_for_training"
        or not record.consent_id
        or not record.extra.get("native_review")
        or not record.target_audio
        or not Path(record.target_audio).is_file()
    ]
    if unauthorized:
        raise ValueError(
            f"Evaluation requires authorized, native-reviewed test rows with target audio; "
            f"{len(unauthorized)} are not approved (for example: {', '.join(unauthorized[:5])})."
        )
    missing_references = [record.id for record in records if not record.reference_translation.strip()]
    if missing_references:
        preview = ", ".join(missing_references[:5])
        raise ValueError(
            f"ASR-BLEU needs a reviewed reference translation for every test item; "
            f"{len(missing_references)} are blank (for example: {preview}). "
            "Do not score ASR hypotheses against missing references."
        )
    try:
        import whisper
    except ImportError:
        raise ImportError("openai-whisper is required for ASR evaluation. Install with: pip install openai-whisper")
    settings = get_settings()
    device = torch.device(settings.device if torch.cuda.is_available() else "cpu")
    model = load_model(checkpoint_path, device)
    codec = NeuralCodec(str(device))
    asr = whisper.load_model(settings.asr_model.replace("openai/whisper-", ""), device=str(device))

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    store = ResearchStore(settings)
    run_id = str(uuid.uuid4())
    hypotheses, references, latencies = [], [], []
    evaluated_language = target_language
    for record in records:
        record_language = record.extra.get("target_language", "en")
        selected_language = evaluated_language or record_language
        if selected_language not in TARGET_LANGUAGES:
            raise ValueError(f"Unsupported target language in evaluation: {selected_language}")
        if record_language != selected_language:
            raise ValueError("A test manifest must contain exactly one target language")
        evaluated_language = selected_language
        source = load_mono(record.source_audio).unsqueeze(0).to(device)
        started = time.perf_counter()
        codes = model.generate(source, torch.tensor([source.shape[1]], device=device))
        waveform = codec.decode(codes)[0].numpy()
        latency_ms = (time.perf_counter() - started) * 1000
        wav_path = destination / f"{record.id}.wav"
        soundfile.write(wav_path, waveform, 24_000)
        transcription = asr.transcribe(
            str(wav_path),
            language=TARGET_LANGUAGES[selected_language]["asr_language"],
            fp16=device.type == "cuda",
        )["text"].strip()
        hypotheses.append(transcription)
        references.append(record.reference_translation)
        latencies.append(latency_ms)
        store.record_evaluation(
            {
                "run_id": run_id,
                "utterance_id": record.id,
                "checkpoint": checkpoint_path,
                "asr_model": settings.asr_model,
                "target_language": selected_language,
                "reference_translation": record.reference_translation,
                "asr_hypothesis": transcription,
                "latency_ms": latency_ms,
                "source_seconds": source.shape[1] / 16_000,
                "generated_waveform_sha256": file_sha256(wav_path),
            }
        )
    bleu = sacrebleu.corpus_bleu(hypotheses, [references])

    # Benchmarking comparisons
    summary = {
        "run_id": run_id,
        "metric": "ASR-BLEU",
        "asr_model": settings.asr_model,
        "target_language": evaluated_language or "en",
        "bleu": round(bleu.score, 2),
        "signature": str(bleu.signature),
        "literature_baseline": None,
        "relative_to_literature_benchmark": None,
        "mean_latency_ms": round(sum(latencies) / len(latencies), 2),
        "p50_latency_ms": round(sorted(latencies)[max(0, int(len(latencies) * 0.50) - 1)], 2),
        "p95_latency_ms": round(sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)], 2),
        "utterances": len(hypotheses),
    }
    (destination / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    store.record_evaluation({"type": "summary", **summary})
    print(json.dumps(summary, indent=2))
    return summary



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", default="artifacts/evaluation")
    parser.add_argument("--target-language", choices=sorted(TARGET_LANGUAGES))
    arguments = parser.parse_args()
    run(arguments.checkpoint, arguments.manifest, arguments.output, arguments.target_language)
