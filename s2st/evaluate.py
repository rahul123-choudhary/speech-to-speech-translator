import argparse
import hashlib
import json
import time
import uuid
from pathlib import Path

import sacrebleu
import soundfile
import torch
import whisper

from .codec import NeuralCodec
from .data import load_mono
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


def run(checkpoint_path: str, manifest_path: str, output_dir: str = "artifacts/evaluation") -> dict:
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
    for record in read_manifest(manifest_path):
        source = load_mono(record.source_audio).unsqueeze(0).to(device)
        started = time.perf_counter()
        codes = model.generate(source, torch.tensor([source.shape[1]], device=device))
        waveform = codec.decode(codes)[0].numpy()
        latency_ms = (time.perf_counter() - started) * 1000
        wav_path = destination / f"{record.id}.wav"
        soundfile.write(wav_path, waveform, 24_000)
        transcription = asr.transcribe(str(wav_path), language="es", fp16=device.type == "cuda")["text"].strip()
        hypotheses.append(transcription)
        references.append(record.reference_translation)
        latencies.append(latency_ms)
        store.record_evaluation(
            {
                "run_id": run_id,
                "utterance_id": record.id,
                "checkpoint": checkpoint_path,
                "asr_model": settings.asr_model,
                "reference_translation": record.reference_translation,
                "asr_hypothesis": transcription,
                "latency_ms": latency_ms,
                "source_seconds": source.shape[1] / 16_000,
                "generated_waveform_sha256": file_sha256(wav_path),
            }
        )
    if not hypotheses:
        raise ValueError(f"No test records in {manifest_path}")
    bleu = sacrebleu.corpus_bleu(hypotheses, [references])
    summary = {
        "run_id": run_id,
        "metric": "ASR-BLEU",
        "asr_model": settings.asr_model,
        "bleu": bleu.score,
        "signature": str(bleu.signature),
        "mean_latency_ms": sum(latencies) / len(latencies),
        "p50_latency_ms": sorted(latencies)[max(0, int(len(latencies) * 0.50) - 1)],
        "p95_latency_ms": sorted(latencies)[max(0, int(len(latencies) * 0.95) - 1)],
        "utterances": len(hypotheses),
    }
    (destination / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--output", default="artifacts/evaluation")
    arguments = parser.parse_args()
    run(arguments.checkpoint, arguments.manifest, arguments.output)
