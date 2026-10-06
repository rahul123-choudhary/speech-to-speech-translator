import torch
import math
from transformers import EncodecModel


class NeuralCodec:
    """Neural-audio codec wrapper used for target units and waveform recovery."""

    def __init__(self, device: str, model_name: str = "facebook/encodec_24khz", bandwidth: float = 6.0):
        self.device = torch.device(device)
        self.model = EncodecModel.from_pretrained(model_name).to(self.device).eval()
        self.model.requires_grad_(False)
        if self.model.config.normalize:
            raise ValueError(
                "This S2ST decoder does not predict EnCodec's per-sample scale. "
                "Use an EnCodec model with normalization disabled."
            )
        self.bandwidth = bandwidth
        self.codebook_size = self.model.config.codebook_size
        self.frame_rate = 75  # EnCodec 24 kHz, 320-sample hop
        self.num_codebooks = round(bandwidth * 1000 / (self.frame_rate * math.log2(self.codebook_size)))

    @torch.no_grad()
    def encode(self, waveforms: torch.Tensor, lengths: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """Return [batch, codebooks, frames] codes and valid frame counts."""
        padding_mask = torch.arange(waveforms.shape[1], device=self.device)[None, :] < lengths[:, None]
        result = self.model.encode(
            waveforms.to(self.device).unsqueeze(1),
            padding_mask=padding_mask.to(self.device).unsqueeze(1),
            bandwidth=self.bandwidth,
        )
        codes = result.audio_codes
        # Transformers returns [frames, batch, codebooks, time] for chunked input.
        if codes.ndim == 4:
            codes = codes.permute(1, 2, 0, 3).reshape(codes.shape[1], codes.shape[2], -1)
        frame_lengths = torch.ceil(lengths.to(self.device) / 320).long()
        return codes.clone(), frame_lengths

    @torch.no_grad()
    def decode(self, codes: torch.Tensor) -> torch.Tensor:
        if codes.ndim != 3:
            raise ValueError("Expected codec units shaped [batch, codebooks, frames]")
        audio = self.model.decode(
            audio_codes=codes.to(self.device).unsqueeze(0), audio_scales=[None]
        ).audio_values
        return audio.squeeze(1).cpu()
