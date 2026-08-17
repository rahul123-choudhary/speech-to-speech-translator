from pathlib import Path

import torch
import torchaudio
from torch.utils.data import Dataset

from .manifest import Utterance, read_manifest


def load_mono(path: str, sample_rate: int = 16_000) -> torch.Tensor:
    waveform, original_rate = torchaudio.load(path)
    waveform = waveform.mean(dim=0)
    if original_rate != sample_rate:
        waveform = torchaudio.functional.resample(waveform, original_rate, sample_rate)
    return waveform.clamp(-1, 1)


def augment_source(waveform: torch.Tensor, sample_rate: int) -> torch.Tensor:
    """Mild waveform-only augmentation; never apply it to validation/test."""
    if torch.rand(()) < 0.5:
        speed = float(torch.empty(1).uniform_(0.93, 1.07))
        new_rate = max(1, round(sample_rate * speed))
        waveform = torchaudio.functional.resample(waveform, sample_rate, new_rate)
        waveform = torchaudio.functional.resample(waveform, new_rate, sample_rate)
    if torch.rand(()) < 0.3:
        waveform = waveform + torch.randn_like(waveform) * 0.002
    return waveform.clamp(-1, 1)


class SpeechPairDataset(Dataset):
    def __init__(self, manifest_path: str, sample_rate: int = 16_000, augment: bool = False):
        self.records = list(read_manifest(manifest_path))
        if not self.records:
            raise ValueError(f"No records in {manifest_path}")
        if any(not record.target_audio for record in self.records):
            raise ValueError("Training requires target_audio for every manifest record")
        self.sample_rate = sample_rate
        self.augment = augment

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict:
        record = self.records[index]
        source = load_mono(record.source_audio, self.sample_rate)
        if self.augment:
            source = augment_source(source, self.sample_rate)
        return {
            "id": record.id,
            "source": source,
            "target": load_mono(record.target_audio, 24_000),
            "reference": record.reference_translation,
        }


def _pad(items: list[torch.Tensor]) -> tuple[torch.Tensor, torch.Tensor]:
    lengths = torch.tensor([item.numel() for item in items], dtype=torch.long)
    output = torch.zeros(len(items), int(lengths.max()))
    for index, item in enumerate(items):
        output[index, : item.numel()] = item
    return output, lengths


def collate_pairs(items: list[dict]) -> dict:
    source, source_lengths = _pad([item["source"] for item in items])
    target, target_lengths = _pad([item["target"] for item in items])
    return {
        "ids": [item["id"] for item in items],
        "source": source,
        "source_lengths": source_lengths,
        "target": target,
        "target_lengths": target_lengths,
        "references": [item["reference"] for item in items],
    }

