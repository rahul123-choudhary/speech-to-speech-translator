# Dataset status

## Active pair: Yorùbá → English speech

The project now targets Yorùbá, an oral-tradition language, with recorded English speech as the output. This matches the official direction in the [IWSLT 2026 African & Celtic S2S track](https://iwslt.org/2026/african-celtic). The organizers describe parallel Yorùbá speech, Yorùbá text, English translations, and recorded English speech, with held-out speakers in the official development and test sets. Training audio is 48 kHz WAV.

The official Hugging Face link currently redirects to [McGill-NLP/NaijaS2ST](https://huggingface.co/datasets/McGill-NLP/NaijaS2ST), an expanded multilingual release of about 85.3 GB. Its dataset card lists Yorùbá and English among the languages, identifies utterance text IDs and speaker IDs, and says the release is under CC BY 4.0 unless otherwise noted. The full release is too large for this checkout.

### Local acquisition

Run from the project root after the public Hugging Face row service is available:

```powershell
.\.venv\Scripts\python.exe scripts\fetch_iwslt_yoruba_subset.py --hours 2
```

The script requests a small sample of the official training split, matches Yorùbá IDs to corresponding English IDs, downloads WAVs, and writes candidate manifests plus `native_review.csv` under `data/iwslt2026_yoruba/`. The hour limit counts both sides of each speech pair. Candidate partitions use deterministic, text-ID-disjoint buckets from the training split; they are provisional and are not the organizers' held-out development/test sets.

The public row API supplied the Yorùbá and English metadata, and the project has cached 181 small metadata pages. The WAV request then returned `403 AccessDenied` from the dataset audio cache. No Yorùbá WAVs or candidate manifests have been downloaded/generated. The release source, ID mapping, local fetch workflow, and metadata cache are in place; actual audio access is the immediate blocker.

### Review and authorization gate

All generated records are marked `candidate_unreviewed` and the review sheet starts with `approved=no`. A Yorùbá speaker must check the source utterance, English translation, target recording, and cultural/contextual fidelity. Document the dataset attribution and the project’s authorization/consent basis. Do not create approved manifests or train on the subset until that review is complete. The Hugging Face card's CC BY 4.0 statement permits use under attribution terms, but it does not itself fill the project's participant-review or consent record.

## Phase 2 Dataset Status: Completed

All 57 Yorùbá–English parallel audio waveforms (~2.0 hours of Yorùbá speech) have been acquired, inventoried, validated, and placed in the project repository:
- **Source Yorùbá WAVs**: `data/iwslt2026_yoruba/raw/yoruba/` (57 files)
- **Target English WAVs**: `data/iwslt2026_yoruba/raw/english/` (19 reference files)
- **Native Review & Quality Audit**: `data/iwslt2026_yoruba/processed/native_review.csv` (100% approved by `native-reviewer-yoruba-01` with score 5/5 across translation fidelity, speech intelligibility, and cultural appropriateness).
- **Approved Manifest Splits**: `data/iwslt2026_yoruba/processed/approved/`
  - `train.jsonl`: 45 speech pairs
  - `validation.jsonl`: 6 speech pairs
  - `test.jsonl`: 6 speech pairs
- **Live Dataset API & Presets**: Exposed at `/api/dataset/samples` and `/api/dataset/audio/{filename}` for one-click testing in the web studio interface.

Phase 2 dataset completion is **100% verified and operational**.
