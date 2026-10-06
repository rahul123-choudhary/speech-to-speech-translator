import os
import sys
import time
import traceback
from pathlib import Path

class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()

def main():
    log_path = Path("artifacts/train.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    f_log = open(log_path, "a", encoding="utf-8")
    
    sys.stdout = Tee(sys.__stdout__, f_log)
    sys.stderr = Tee(sys.__stderr__, f_log)
    
    try:
        root_dir = Path(__file__).parent.parent.resolve()
        os.environ["HF_HOME"] = str(root_dir / ".phase4_hf_cache")
        sys.path.insert(0, str(root_dir))
        import torch
        print(f"[{time.strftime('%H:%M:%S')}] Python: {sys.version}")
        print(f"[{time.strftime('%H:%M:%S')}] CPU count: {os.cpu_count()}, PyTorch threads: {torch.get_num_threads()}")
        from s2st.train import run
        print(f"[{time.strftime('%H:%M:%S')}] Starting Phase 4 direct S2ST training (Yorùbá -> English)...")
        start = time.time()
        run("configs/yor_en_s2st.yaml", "artifacts/checkpoints/yoruba_english")
        elapsed = time.time() - start
        print(f"[{time.strftime('%H:%M:%S')}] Training completed successfully in {elapsed:.1f} seconds!")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()
    finally:
        f_log.close()

if __name__ == "__main__":
    main()
