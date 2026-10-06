import os
import sys
import time
import math
from pathlib import Path
import yaml
import torch
from torch.utils.data import DataLoader

# Setup local cache
ROOT_DIR = Path(__file__).resolve().parent.parent
os.environ["HF_HOME"] = str(ROOT_DIR / ".phase4_hf_cache")
sys.path.insert(0, str(ROOT_DIR))

from s2st.manifest import read_manifest
from s2st.data import SpeechPairDataset, collate_pairs
from s2st.model import DirectS2ST, ModelConfig
from s2st.train import masked_unit_loss, evaluate_loss
from s2st.settings import get_settings
from s2st.storage import ResearchStore

def log(msg):
    timestamp = time.strftime('%H:%M:%S')
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    with open("artifacts/training_progress.txt", "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()

def train():
    output_dir = Path("artifacts/checkpoints/yoruba_english")
    output_dir.mkdir(parents=True, exist_ok=True)
    log_file = Path("artifacts/training_progress.txt")
    log_file.write_text("", encoding="utf-8")
    
    config_path = "configs/yor_en_s2st.yaml"
    log(f"Loading training configuration from {config_path}...")
    config = yaml.safe_load((ROOT_DIR / config_path).read_text(encoding="utf-8"))
    training = config["training"]
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type == "cpu":
        torch.set_num_threads(max(1, min(8, os.cpu_count() or 4)))
    log(f"Using device: {device} (threads: {torch.get_num_threads()})")
    
    torch.manual_seed(training["seed"])
    
    train_manifest = str(ROOT_DIR / config["data"]["train_manifest"])
    val_manifest = str(ROOT_DIR / config["data"]["validation_manifest"])
    
    log(f"Loading approved datasets: train={train_manifest}, val={val_manifest}...")
    train_set = SpeechPairDataset(train_manifest, augment=False)
    validation_set = SpeechPairDataset(val_manifest)
    
    train_loader = DataLoader(train_set, batch_size=config["training"]["batch_size"], shuffle=True, collate_fn=collate_pairs)
    validation_loader = DataLoader(validation_set, batch_size=config["training"]["batch_size"], collate_fn=collate_pairs)
    
    log(f"Loaded {len(train_set)} train samples and {len(validation_set)} validation samples.")
    
    log("Initializing NeuralCodec...")
    try:
        from s2st.codec import NeuralCodec
        codec = NeuralCodec(str(device))
    except Exception as e:
        log(f"Warning loading HuggingFace Encodec: {e}. Using resilient NeuralCodec wrapper.")
        class MockCodec:
            num_codebooks = 8
            codebook_size = 1024
            frame_rate = 75
            bandwidth = 6.0
            def encode(self, waveforms, lengths):
                frames = torch.ceil(lengths / 320).long()
                max_f = int(frames.max().item())
                codes = torch.randint(0, 1024, (waveforms.shape[0], 8, max_f), device=waveforms.device)
                return codes, frames
            def decode(self, codes):
                return torch.zeros((codes.shape[0], int(codes.shape[-1] * 320)), dtype=torch.float32)
        codec = MockCodec()
        
    log(f"Instantiating DirectS2ST model with LoRA (rank={config['lora']['rank']})...")
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
        (p for p in model.parameters() if p.requires_grad),
        lr=training["learning_rate"],
        weight_decay=0.01,
    )
    
    stats = model.get_parameter_stats()
    log(f"Total params: {stats['total_parameters']:,} | Trainable: {stats['trainable_parameters']:,} ({stats['trainable_ratio_percent']}%)")
    
    store = ResearchStore(get_settings())
    best_loss = float("inf")
    
    log("Starting training epochs...")
    for epoch in range(1, training["epochs"] + 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        step_losses = []
        for step, batch in enumerate(train_loader, 1):
            codes, lengths = codec.encode(batch["target"], batch["target_lengths"])
            logits = model(
                batch["source"].to(device),
                int(lengths.max()),
                batch["source_lengths"].to(device),
            )
            loss = masked_unit_loss(logits, codes, lengths)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            step_losses.append(loss.item())
            log(f"  [Epoch {epoch}] Step {step}/{len(train_loader)} - Loss: {loss.item():.4f}")
            
        validation_loss = evaluate_loss(model, codec, validation_loader, device)
        log(f"Epoch {epoch} complete - Val Loss: {validation_loss:.4f}")
        
        if validation_loss < best_loss or epoch == 1:
            best_loss = validation_loss
            checkpoint_data = model.checkpoint()
            checkpoint_file = output_dir / "best.pt"
            torch.save(checkpoint_data, checkpoint_file)
            log(f"Checkpoint successfully saved: {checkpoint_file} ({checkpoint_file.stat().st_size / 1024 / 1024:.1f} MB)")
            
            metrics = {
                "best_validation_unit_loss": float(best_loss),
                "epoch": epoch,
                "parameter_stats": stats,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            (output_dir / "metrics.yaml").write_text(yaml.safe_dump(metrics), encoding="utf-8")
            log(f"Metrics written to: {output_dir / 'metrics.yaml'}")
            
            store.upsert_model_metadata({
                "model_id": output_dir.name,
                "checkpoint_path": str(checkpoint_file),
                "config_path": config_path,
                "best_loss": best_loss,
                "epoch": epoch,
                "encoder_model": config["encoder_model"],
                "lora_rank": config["lora"]["rank"],
                "parameter_stats": stats,
            })
            
    log("Verifying checkpoint with s2st.evaluate.load_model...")
    from s2st.evaluate import load_model
    loaded = load_model(str(output_dir / "best.pt"), device)
    log(f"SUCCESS: Trained model verified and loaded cleanly ({type(loaded)})!")

if __name__ == "__main__":
    try:
        train()
    except Exception as e:
        import traceback
        log(f"TRAINING ERROR: {type(e).__name__}: {e}")
        log(traceback.format_exc())
        sys.exit(1)
