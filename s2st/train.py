import argparse
import math
from pathlib import Path

import torch
import yaml
from torch.nn import functional as functional
from torch.utils.data import DataLoader

from .codec import NeuralCodec
from .data import SpeechPairDataset, collate_pairs
from .model import DirectS2ST, ModelConfig


def masked_unit_loss(logits: torch.Tensor, codes: torch.Tensor, frame_lengths: torch.Tensor) -> torch.Tensor:
    """Cross entropy only over valid codec frames, never padding."""
    total = logits.new_zeros(())
    count = 0
    for index, valid_frames in enumerate(frame_lengths.tolist()):
        if valid_frames <= 0:
            continue
        target = codes[index, :, :valid_frames]
        # Cross entropy expects class/vocabulary on dimension 1: [codebooks, vocab, frames].
        prediction = logits[index, :, :valid_frames].transpose(1, 2)
        total = total + functional.cross_entropy(prediction, target)
        count += 1
    return total / max(count, 1)


def evaluate_loss(model: DirectS2ST, codec: NeuralCodec, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    losses: list[float] = []
    with torch.inference_mode():
        for batch in loader:
            codes, lengths = codec.encode(batch["target"], batch["target_lengths"])
            logits = model(batch["source"].to(device), int(lengths.max()))
            losses.append(float(masked_unit_loss(logits, codes, lengths).cpu()))
    return sum(losses) / len(losses)


def run(config_path: str, output: str) -> None:
    config = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    training = config["training"]
    torch.manual_seed(training["seed"])
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_set = SpeechPairDataset(config["data"]["train_manifest"], augment=training["augment_train"])
    validation_set = SpeechPairDataset(config["data"]["validation_manifest"])
    train_loader = DataLoader(train_set, batch_size=training["batch_size"], shuffle=True, collate_fn=collate_pairs)
    validation_loader = DataLoader(validation_set, batch_size=training["batch_size"], collate_fn=collate_pairs)
    codec = NeuralCodec(str(device))
    model = DirectS2ST(
        ModelConfig(
            encoder_model=config["encoder_model"],
            lora_rank=config["lora"]["rank"],
            lora_alpha=config["lora"]["alpha"],
            lora_dropout=config["lora"]["dropout"],
            codec_codebooks=codec.num_codebooks,
            codec_vocab_size=codec.codebook_size,
            max_target_frames=math.ceil(config["max_seconds"] * codec.frame_rate),
        )
    ).to(device)
    optimizer = torch.optim.AdamW(
        (parameter for parameter in model.parameters() if parameter.requires_grad),
        lr=training["learning_rate"],
        weight_decay=0.01,
    )
    output_path = Path(output)
    output_path.mkdir(parents=True, exist_ok=True)
    best_loss, stalled = float("inf"), 0
    for epoch in range(1, training["epochs"] + 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        for step, batch in enumerate(train_loader, 1):
            codes, lengths = codec.encode(batch["target"], batch["target_lengths"])
            logits = model(batch["source"].to(device), int(lengths.max()))
            loss = masked_unit_loss(logits, codes, lengths) / training["gradient_accumulation"]
            loss.backward()
            if step % training["gradient_accumulation"] == 0 or step == len(train_loader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                optimizer.zero_grad(set_to_none=True)
        validation_loss = evaluate_loss(model, codec, validation_loader, device)
        print(f"epoch={epoch} validation_unit_loss={validation_loss:.4f}")
        if validation_loss < best_loss:
            best_loss, stalled = validation_loss, 0
            torch.save(model.checkpoint(), output_path / "best.pt")
            (output_path / "metrics.yaml").write_text(
                yaml.safe_dump({"best_validation_unit_loss": best_loss, "epoch": epoch}), encoding="utf-8"
            )
        else:
            stalled += 1
            if stalled >= training["early_stopping_patience"]:
                print("early stopping")
                break


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(args.config, args.output)
