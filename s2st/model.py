from dataclasses import asdict, dataclass

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

    def forward(self, source: torch.Tensor, output_frames: int) -> torch.Tensor:
        if output_frames > self.config.max_target_frames:
            raise ValueError("Utterance exceeds max_target_frames; segment it before training")
        encoded = self.encoder(input_values=source).last_hidden_state
        queries = self.position.weight[:output_frames].unsqueeze(0).expand(source.shape[0], -1, -1)
        decoded = self.decoder(tgt=queries, memory=encoded)
        return torch.stack([head(decoded) for head in self.heads], dim=1)

    @torch.inference_mode()
    def generate(self, source: torch.Tensor, source_lengths: torch.Tensor) -> torch.Tensor:
        # Conservative duration estimate; record timing and revise with pilot data.
        frames = torch.clamp((source_lengths.max().float() / 16_000 * 75 * 1.1).long(), min=1)
        logits = self(source, int(frames))
        return logits.argmax(dim=-1)

    def checkpoint(self) -> dict:
        return {"config": asdict(self.config), "state_dict": self.state_dict()}

