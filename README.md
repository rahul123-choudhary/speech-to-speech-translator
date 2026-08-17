# Direct Quechua Speech → Spanish Speech Translation

This repository implements the requested low-resource, direct speech-to-speech
translation (S2ST) research system. The deployed model maps Quechua acoustic
features directly to Spanish neural-audio codec units and reconstructs a Spanish
waveform. It does not run ASR, machine translation, or text-to-speech at
inference time.

The first experiment is deliberately small-hours: **1h40m** of aligned
Quechua-to-Spanish data from the IWSLT Quechua–Spanish release, with a strict
train/validation/test split. The optional 48h transcribed Quechua corpus is
kept for a separately labelled unconstrained encoder-adaptation experiment.

## Output languages

The live API lets the user select one of five target languages: Spanish (`es`),
English (`en`), Hindi (`hi`), French (`fr`), or Portuguese (`pt`). Each is a
separate direct model: Quechua speech → selected-language speech. The system
must not translate through Spanish text or speech to produce any other output.

Call `GET /v1/languages` before creating a session. It returns `ready` only
when that language has its own trained checkpoint; otherwise it reports
`setup_required`. Select the output language when creating the session:

```json
POST /v1/sessions
{
  "consented_audio_processing": true,
  "target_language": "fr"
}
```

The included IWSLT corpus supports Spanish only. English, Hindi, French, and
Portuguese each need aligned Quechua speech + human-approved target-language
references, licensed target speech, review records, and a separately trained
checkpoint before their status can be `ready`.

Create the English reference-review template from the existing 823 Quechua
source utterances:

```powershell
python -m s2st.english --reference-template data/manifests_en/english_references.tsv
```

After an identified translator and reviewer approve the English references,
build English candidates and target-audio review records:

```powershell
python -m s2st.english `
  --english-references data/manifests_en/english_references.tsv `
  --target-audio-dir data/targets/iwslt_que_eng_2h `
  --target-speech-generator "<licensed English voice and version>" `
  --consent-id "<approved consent record>"

python -m s2st.prepare `
  --input data/manifests_en/candidates.jsonl `
  --approvals data/manifests_en/native_review.csv `
  --output data/manifests_en `
  --sync-atlas
```

`s2st.english` never translates Spanish references automatically. This avoids
mistaking machine-generated English for a community-approved translation.

For Hindi, French, or Portuguese, create the same review-gated material with
the general target-language workflow (replace `fr` with `hi` or `pt`):

```powershell
python -m s2st.target_language --target-language fr `
  --reference-template data/manifests_fr/target_references.tsv

# After human translation and review:
python -m s2st.target_language --target-language fr `
  --target-references data/manifests_fr/target_references.tsv `
  --target-audio-dir data/targets/iwslt_que_fra_2h `
  --target-speech-generator "<licensed French voice and version>" `
  --consent-id "<approved consent record>"

python -m s2st.prepare `
  --input data/manifests_fr/candidates.jsonl `
  --approvals data/manifests_fr/native_review.csv `
  --output data/manifests_fr `
  --sync-atlas
```

Use `configs/que_eng_2h.yaml`, `configs/que_hin_2h.yaml`,
`configs/que_fra_2h.yaml`, or `configs/que_por_2h.yaml` to train the matching
model. Set the matching `S2ST_CHECKPOINT_<LANGUAGE>` value in `.env` to make
the selected language available in the live API.

For a non-commercial research draft only, you can generate a separate TSV of
offline Spanish-to-English machine drafts with NLLB-200. These rows are marked
`machine_draft`, have no reviewer ID, and are rejected by the English manifest
builder until a human translator and reviewer change them to `approved`:

```powershell
python -m s2st.draft_english --output data/manifests_en/english_machine_drafts.tsv
```

NLLB is used for offline draft construction only—not in the deployed direct
speech-to-speech route. Preserve its model/version in the TSV and document its
CC-BY-NC research-use terms.

## Data

1. Obtain the IWSLT Quechua–Spanish data from the project release and follow
   its CC BY-NC-ND 3.0 terms. It contains the aligned 1h40m speech-to-translation
   set and describes the optional 48h transcription-only extension.
2. Place and resample the source clips at 16 kHz.
3. Prepare a target Spanish speech waveform per reference translation using a
   Spanish voice permitted for research use; native Spanish reviewers must
   verify content, pronunciation, and cultural appropriateness. This creates
   speech supervision offline only, so live translation remains text-free.
4. Use the review-gated manifest workflow in
   [`data/manifests/README.md`](data/manifests/README.md). It blocks
   unreviewed target speech from reaching training and rejects speaker leakage
   in the source-release split by re-splitting deterministically by speaker.

The data choice and its limitations are documented in
[`DATASETS.md`](DATASETS.md). Do not claim a direct S2ST benchmark against a
text-only reference corpus until target-speech supervision and consent have been
documented.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set Firebase and MongoDB Atlas values in `.env`, then run:

```powershell
python -m s2st.train --config configs/que_spa_2h.yaml --output artifacts/que_spa_2h
python -m s2st.evaluate --checkpoint artifacts/que_spa_2h/best.pt --manifest data/manifests/test.jsonl
uvicorn s2st.api:app --host 0.0.0.0 --port 8000
```

`prepare` validates paths and creates a deterministic, speaker-aware split; it
does not download a corpus or synthesize audio. Dataset access, voice licensing,
and community consent remain research-team responsibilities.

## Evaluation

The evaluator transcribes synthesized Spanish using the configured ASR model,
then computes case-sensitive sacreBLEU against the held-out Spanish references.
It additionally writes per-utterance latency, ASR text, and model metadata to
MongoDB Atlas. Use the included human-evaluation template for naturalness,
intelligibility, translation adequacy, and cultural/contextual appropriateness.

Report ASR-BLEU alongside ASR choice/version, codec, target-speech construction,
split protocol, mean/p95 latency, and human scores with confidence intervals.
The commonly cited 17.7 BLEU Quechua result is a text-output speech translation
comparison—not automatically comparable to ASR-BLEU on synthesized speech.

## Live pilot

`/v1/sessions` creates a Firebase-authenticated community session. Send 16-kHz
mono PCM chunks over its WebSocket (include the Firebase ID token as the `token`
query value); send `{"event":"finalize"}` at the end of the turn. The server
returns synthesized WAV audio and stores only the metadata and consented pilot
records specified in `s2st/storage.py`.

See [`PROTOCOL.md`](PROTOCOL.md) for the phase-by-phase study protocol.
