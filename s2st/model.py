from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import torch
from peft import LoraConfig, TaskType, get_peft_model
from torch import nn
from transformers import AutoModel


@dataclass
class ModelConfig:
    encoder_model: str = "facebook/wav2vec2-xls-r-300m"
    lora_rank: int = 8
    lora_alpha: int = 16
    lora_dropout: float = 0.05
    decoder_layers: int = 4
    decoder_heads: int = 8
    codec_codebooks: int = 8
    codec_vocab_size: int = 1024
    max_target_frames: int = 1200


class DirectS2ST(nn.Module):
    """Speech encoder → codec-unit decoder, with no ASR/MT/TTS inference path."""

    def __init__(self, config: ModelConfig):
        super().__init__()
        self.config = config
        cache_root = Path(__file__).resolve().parent.parent / ".phase4_hf_cache"
        if cache_root.exists():
            import os
            os.environ.setdefault("HF_HOME", str(cache_root))
        try:
            base_encoder = AutoModel.from_pretrained(config.encoder_model, local_files_only=True)
        except Exception:
            base_encoder = AutoModel.from_pretrained(config.encoder_model)
        lora = LoraConfig(
            task_type=TaskType.FEATURE_EXTRACTION,
            r=config.lora_rank,
            lora_alpha=config.lora_alpha,
            lora_dropout=config.lora_dropout,
            target_modules=["q_proj", "k_proj", "v_proj", "out_proj"],
        )
        self.encoder = get_peft_model(base_encoder, lora)
        hidden = base_encoder.config.hidden_size
        self.position = nn.Embedding(config.max_target_frames, hidden)
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=hidden, nhead=config.decoder_heads, dim_feedforward=hidden * 4, batch_first=True
        )
        self.decoder = nn.TransformerDecoder(decoder_layer, num_layers=config.decoder_layers)
        self.heads = nn.ModuleList(
            [nn.Linear(hidden, config.codec_vocab_size) for _ in range(config.codec_codebooks)]
        )

    def forward(
        self,
        source: torch.Tensor,
        output_frames: int,
        source_lengths: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if output_frames > self.config.max_target_frames:
            raise ValueError("Utterance exceeds max_target_frames; segment it before training")
        attention_mask = None
        if source_lengths is not None:
            positions = torch.arange(source.shape[1], device=source.device).unsqueeze(0)
            attention_mask = (positions < source_lengths.to(source.device).unsqueeze(1)).long()
        encoded = self.encoder(input_values=source, attention_mask=attention_mask).last_hidden_state
        memory_key_padding_mask = None
        if attention_mask is not None:
            enc_cfg = getattr(self.encoder, "config", None)
            if not hasattr(enc_cfg, "conv_kernel") and hasattr(self.encoder, "base_model"):
                enc_cfg = getattr(getattr(self.encoder.base_model, "model", self.encoder.base_model), "config", enc_cfg)
            conv_kernel = getattr(enc_cfg, "conv_kernel", [10, 3, 3, 3, 3, 2, 2])
            conv_stride = getattr(enc_cfg, "conv_stride", [5, 2, 2, 2, 2, 2, 2])
            feature_lengths = source_lengths.to(source.device)
            for kernel, stride in zip(conv_kernel, conv_stride):
                feature_lengths = torch.div(feature_lengths - kernel, stride, rounding_mode="floor") + 1
            feature_lengths = feature_lengths.clamp(min=1, max=encoded.shape[1])
            encoded_positions = torch.arange(encoded.shape[1], device=source.device).unsqueeze(0)
            memory_key_padding_mask = encoded_positions >= feature_lengths.unsqueeze(1)
        queries = self.position.weight[:output_frames].unsqueeze(0).expand(source.shape[0], -1, -1)
        decoded = self.decoder(tgt=queries, memory=encoded, memory_key_padding_mask=memory_key_padding_mask)
        return torch.stack([head(decoded) for head in self.heads], dim=1)

    @torch.inference_mode()
    def generate(self, source: torch.Tensor, source_lengths: torch.Tensor) -> torch.Tensor:
        # Conservative duration estimate; record timing and revise with pilot data.
        frames = torch.clamp((source_lengths.max().float() / 16_000 * 75 * 1.1).long(), min=1)
        logits = self(source, int(frames), source_lengths)
        return logits.argmax(dim=-1)

    def get_parameter_stats(self) -> dict[str, Any]:
        """Compute parameter efficiency (trainable LoRA & decoder params vs frozen base encoder)."""
        total_params = sum(p.numel() for p in self.parameters())
        trainable_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        frozen_params = total_params - trainable_params
        return {
            "total_parameters": total_params,
            "trainable_parameters": trainable_params,
            "frozen_parameters": frozen_params,
            "trainable_ratio_percent": round((trainable_params / total_params) * 100, 2) if total_params else 0.0,
            "lora_rank": self.config.lora_rank,
            "lora_alpha": self.config.lora_alpha,
            "base_encoder": self.config.encoder_model,
        }

    def checkpoint(self) -> dict:
        return {
            "config": asdict(self.config),
            "state_dict": self.state_dict(),
            "parameter_stats": self.get_parameter_stats(),
        }
