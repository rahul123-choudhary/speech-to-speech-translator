import sys
import os
from pathlib import Path

print(f"Python: {sys.executable}")
modules_to_test = ["torch", "transformers", "whisper", "edge_tts", "gtts", "soundfile", "numpy", "peft", "yaml"]
results = {}
for m in modules_to_test:
    try:
        __import__(m)
        results[m] = "AVAILABLE"
    except ImportError as e:
        results[m] = f"MISSING ({e})"
    except Exception as e:
        results[m] = f"ERROR ({e})"

for m, status in results.items():
    print(f"  - {m}: {status}")

with open("artifacts/env_check.txt", "w", encoding="utf-8") as f:
    for m, status in results.items():
        f.write(f"{m}: {status}\n")
